from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from core.rbac import ROLE_GROUPS, ROLES


class Command(BaseCommand):
    help = "Assign exactly one DomainTwin RBAC role to a Django user."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("role", choices=ROLES)

    def handle(self, *args, **options):
        username = options["username"]
        role = options["role"]
        User = get_user_model()
        username_field = User.USERNAME_FIELD
        user = User._default_manager.filter(**{username_field: username}).first()
        if user is None:
            raise CommandError(f"User {username!r} was not found.")

        domaintwin_groups = list(Group.objects.filter(name__in=ROLE_GROUPS.values()))
        if domaintwin_groups:
            user.groups.remove(*domaintwin_groups)

        group, _ = Group.objects.get_or_create(name=ROLE_GROUPS[role])
        user.groups.add(group)

        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned DomainTwin role {role} to {user.get_username()}."
            )
        )
