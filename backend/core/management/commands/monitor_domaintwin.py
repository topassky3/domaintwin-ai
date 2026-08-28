from __future__ import annotations

import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.monitoring import run_monitoring_cycle


class Command(BaseCommand):
    help = (
        "Run DomainTwin Monitoring Lite once, or continuously as a separate worker. "
        "Only active organizations/domains with an active provider binding and known-good baseline are evaluated."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization",
            dest="organization_slug",
            help="Limit the cycle to one Organization slug.",
        )
        parser.add_argument(
            "--domain",
            dest="domain_names",
            action="append",
            help="Limit the cycle to one managed domain. Repeat for multiple domains.",
        )
        parser.add_argument(
            "--loop",
            action="store_true",
            help="Repeat cycles continuously. Run this as a separate worker, never inside the web process.",
        )
        parser.add_argument(
            "--interval-seconds",
            type=int,
            help="Loop interval override. Defaults to DOMAIN_MONITOR_INTERVAL_SECONDS.",
        )

    def handle(self, *args, **options):
        loop = bool(options["loop"])
        interval = options["interval_seconds"]
        if interval is None:
            interval = int(settings.DOMAIN_MONITOR_INTERVAL_SECONDS)
        if loop and interval < 10:
            raise CommandError("Monitoring loop interval must be at least 10 seconds.")

        organization_slug = options.get("organization_slug") or None
        domain_names = options.get("domain_names") or None

        try:
            while True:
                summary = run_monitoring_cycle(
                    organization_slug=organization_slug,
                    domain_names=domain_names,
                )
                self.stdout.write(json.dumps(summary, sort_keys=True))
                if not loop:
                    return
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("DomainTwin monitoring worker stopped."))
