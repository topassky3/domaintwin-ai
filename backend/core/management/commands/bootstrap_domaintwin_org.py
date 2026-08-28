from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from core.models import Membership, Organization
from core.rbac import role_for_user


class Command(BaseCommand):
    help = (
        "Create an Organization and explicit memberships using each user's current "
        "P2 DomainTwin role. Safe to re-run during the P3 migration."
    )

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("name")
        parser.add_argument(
            "--username",
            dest="usernames",
            action="append",
            required=True,
            help="Existing Django username to add. Repeat for multiple users.",
        )

    def handle(self, *args, **options):
        slug = str(options["slug"]).strip()
        name = str(options["name"]).strip()
        usernames = list(dict.fromkeys(options["usernames"]))

        if not name:
            raise CommandError("Organization name cannot be empty.")
        if not slug or slugify(slug) != slug:
            raise CommandError("Organization slug must already be normalized lowercase slug text.")

        User = get_user_model()
        username_field = User.USERNAME_FIELD
        users = []
        for username in usernames:
            user = User._default_manager.filter(**{username_field: username}).first()
            if user is None:
                raise CommandError(f"User {username!r} was not found.")
            users.append(user)

        with transaction.atomic():
            organization, created = Organization.objects.get_or_create(
                slug=slug,
                defaults={"name": name},
            )
            if not created and organization.name != name:
                raise CommandError(
                    f"Organization slug {slug!r} already exists with name {organization.name!r}."
                )

            created_count = 0
            updated_count = 0
            for user in users:
                role = role_for_user(user) or Membership.Role.VIEWER
                _, membership_created = Membership.objects.update_or_create(
                    organization=organization,
                    user=user,
                    defaults={"role": role, "is_active": True},
                )
                if membership_created:
                    created_count += 1
                else:
                    updated_count += 1

        action = "Created" if created else "Reused"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} organization {organization.slug} ({organization.id}); "
                f"memberships created={created_count}, updated={updated_count}."
            )
        )
