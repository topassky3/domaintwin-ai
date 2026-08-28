from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from core.demo_readiness import build_demo_readiness
from core.models import Organization


class Command(BaseCommand):
    help = "Run the deterministic DomainTwin hackathon demo preflight for one organization."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True, help="Organization slug to validate.")
        parser.add_argument("--json", action="store_true", dest="as_json", help="Emit machine-readable JSON.")

    def handle(self, *args, **options):
        slug = options["organization"]
        try:
            organization = Organization.objects.get(slug=slug, is_active=True)
        except Organization.DoesNotExist as exc:
            raise CommandError(f"Active DomainTwin organization '{slug}' was not found.") from exc

        payload = build_demo_readiness(organization)
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, sort_keys=True))
        else:
            self.stdout.write(f"DomainTwin demo readiness · {organization.slug}")
            for check in payload["checks"]:
                self.stdout.write(f"[{check['status']}] {check['label']}: {check['detail']}")
            self.stdout.write(
                f"STATUS={payload['status']} blockers={payload['blockerCount']} warnings={payload['warningCount']}"
            )

        if payload["status"] != "READY":
            raise CommandError(
                f"Demo preflight blocked by {payload['blockerCount']} required check(s)."
            )
