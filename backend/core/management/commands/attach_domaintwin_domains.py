from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import (
    DomainSnapshot,
    EmergencyDomainPlan,
    HealthObservation,
    Incident,
    KnownGoodSnapshot,
    ManagedDomain,
    Organization,
    RecoveryPlan,
    canonical_domain_name,
)


LEGACY_DOMAIN_SOURCES = (
    (DomainSnapshot, "domain_name"),
    (KnownGoodSnapshot, "domain_name"),
    (HealthObservation, "domain_name"),
    (Incident, "domain_name"),
    (RecoveryPlan, "domain_name"),
    (EmergencyDomainPlan, "source_domain_name"),
)


class Command(BaseCommand):
    help = (
        "Attach explicit domain ownership roots to an Organization without rewriting "
        "legacy DNS evidence. Safe to re-run; --detach removes only the ownership root."
    )

    def add_arguments(self, parser):
        parser.add_argument("organization_slug")
        parser.add_argument(
            "--domain",
            dest="domains",
            action="append",
            default=[],
            help="Domain to attach. Repeat for multiple domains.",
        )
        parser.add_argument(
            "--from-legacy",
            action="store_true",
            help="Also attach every distinct legacy source-domain name currently stored.",
        )
        parser.add_argument(
            "--detach",
            action="store_true",
            help="Delete matching ManagedDomain ownership roots instead of attaching them.",
        )

    def handle(self, *args, **options):
        slug = str(options["organization_slug"]).strip()
        try:
            organization = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist as exc:
            raise CommandError(f"Organization {slug!r} was not found.") from exc

        raw_names = list(options["domains"])
        if options["from_legacy"]:
            for model, field in LEGACY_DOMAIN_SOURCES:
                raw_names.extend(
                    model.objects.exclude(**{field: ""})
                    .values_list(field, flat=True)
                    .distinct()
                )

        try:
            names = sorted({canonical_domain_name(name) for name in raw_names})
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if not names:
            raise CommandError("Provide at least one --domain or use --from-legacy.")

        conflicts = list(
            ManagedDomain.objects.filter(name__in=names)
            .exclude(organization=organization)
            .values_list("name", "organization__slug")
        )
        if conflicts:
            detail = ", ".join(f"{name} -> {owner}" for name, owner in conflicts)
            raise CommandError(f"Domain ownership conflict: {detail}")

        with transaction.atomic():
            if options["detach"]:
                deleted, _ = ManagedDomain.objects.filter(
                    organization=organization,
                    name__in=names,
                ).delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Detached {deleted} managed-domain root(s) from {organization.slug}."
                    )
                )
                return

            created_count = 0
            reused_count = 0
            for name in names:
                managed, created = ManagedDomain.objects.get_or_create(
                    name=name,
                    defaults={
                        "organization": organization,
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                else:
                    if not managed.is_active:
                        managed.is_active = True
                        managed.save(update_fields=["is_active", "updated_at"])
                    reused_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Attached domains to {organization.slug}; "
                f"created={created_count}, reused={reused_count}."
            )
        )
