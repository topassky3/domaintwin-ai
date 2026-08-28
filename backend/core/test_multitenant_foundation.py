from __future__ import annotations

import uuid
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Membership, Organization
from .rbac import ADMIN, APPROVER, OPERATOR, ROLES, ROLE_GROUPS, VIEWER


class MultiTenantFoundationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="operator", password="pw")
        operator_group, _ = Group.objects.get_or_create(name=ROLE_GROUPS[OPERATOR])
        self.user.groups.add(operator_group)

    def test_organization_uses_non_enumerable_uuid_identity(self):
        organization = Organization.objects.create(name="Acme", slug="acme")
        self.assertIsInstance(organization.id, uuid.UUID)
        self.assertEqual(Organization.objects.get(slug="acme"), organization)

    def test_membership_roles_are_compatible_with_p2_roles(self):
        self.assertEqual(set(Membership.Role.values), set(ROLES))
        self.assertEqual(
            set(Membership.Role.values),
            {VIEWER, OPERATOR, APPROVER, ADMIN},
        )

    def test_same_user_can_hold_different_roles_per_organization(self):
        first = Organization.objects.create(name="First", slug="first")
        second = Organization.objects.create(name="Second", slug="second")
        Membership.objects.create(organization=first, user=self.user, role=Membership.Role.ADMIN)
        Membership.objects.create(organization=second, user=self.user, role=Membership.Role.VIEWER)

        self.assertEqual(
            Membership.objects.get(organization=first, user=self.user).role,
            ADMIN,
        )
        self.assertEqual(
            Membership.objects.get(organization=second, user=self.user).role,
            VIEWER,
        )

    def test_duplicate_membership_is_rejected_by_database(self):
        organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(organization=organization, user=self.user, role=Membership.Role.OPERATOR)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(
                    organization=organization,
                    user=self.user,
                    role=Membership.Role.ADMIN,
                )

    def test_bootstrap_command_copies_current_p2_role_and_is_idempotent(self):
        first_out = StringIO()
        call_command(
            "bootstrap_domaintwin_org",
            "legacy",
            "Legacy Workspace",
            "--username",
            self.user.get_username(),
            stdout=first_out,
        )
        organization = Organization.objects.get(slug="legacy")
        membership = Membership.objects.get(organization=organization, user=self.user)
        self.assertEqual(membership.role, OPERATOR)
        self.assertTrue(membership.is_active)
        self.assertIn("Created organization legacy", first_out.getvalue())

        second_out = StringIO()
        call_command(
            "bootstrap_domaintwin_org",
            "legacy",
            "Legacy Workspace",
            "--username",
            self.user.get_username(),
            stdout=second_out,
        )
        self.assertEqual(Organization.objects.filter(slug="legacy").count(), 1)
        self.assertEqual(Membership.objects.filter(organization=organization, user=self.user).count(), 1)
        self.assertIn("Reused organization legacy", second_out.getvalue())

    def test_bootstrap_validates_all_users_before_creating_organization(self):
        with self.assertRaisesMessage(Exception, "was not found"):
            call_command(
                "bootstrap_domaintwin_org",
                "unsafe",
                "Unsafe Workspace",
                "--username",
                "missing-user",
            )
        self.assertFalse(Organization.objects.filter(slug="unsafe").exists())
