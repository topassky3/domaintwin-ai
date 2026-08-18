from django.db import models


class DomainSnapshot(models.Model):
    domain_name = models.CharField(max_length=253, db_index=True)
    version = models.PositiveIntegerField()
    records = models.JSONField(default=list)
    fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["domain_name", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["domain_name", "version"],
                name="unique_domain_snapshot_version",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("DomainSnapshot rows are immutable once created.")
        return super().save(*args, **kwargs)


class KnownGoodSnapshot(models.Model):
    domain_name = models.CharField(max_length=253, unique=True)
    snapshot = models.ForeignKey(
        DomainSnapshot,
        on_delete=models.PROTECT,
        related_name="known_good_for",
    )
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["domain_name"]


class HealthObservation(models.Model):
    domain_name = models.CharField(max_length=253, db_index=True)
    dns_resolution = models.JSONField(default=dict)
    http = models.JSONField(default=dict)
    https = models.JSONField(default=dict)
    availability_ok = models.BooleanField()
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_at", "-id"]


class Incident(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        RESOLVED = "RESOLVED", "Resolved"

    domain_name = models.CharField(max_length=253, db_index=True)
    baseline_snapshot = models.ForeignKey(
        DomainSnapshot,
        on_delete=models.PROTECT,
        related_name="incidents",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    score = models.PositiveSmallIntegerField(default=0)
    severity = models.CharField(max_length=16, default="LOW")
    factors = models.JSONField(default=list)
    evidence = models.JSONField(default=dict)
    evidence_fingerprint = models.CharField(max_length=64)
    opened_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["domain_name"],
                condition=models.Q(status="OPEN"),
                name="unique_open_incident_per_domain",
            )
        ]


class IncidentEvent(models.Model):
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="timeline",
    )
    sequence = models.PositiveIntegerField()
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["incident", "sequence"],
                name="unique_incident_event_sequence",
            )
        ]
