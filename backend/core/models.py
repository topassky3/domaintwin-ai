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


class RecoveryPlan(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "PREVIEW", "Preview"
        APPROVED = "APPROVED", "Approved"
        APPLYING = "APPLYING", "Applying"
        RECOVERED = "RECOVERED", "Recovered"
        PARTIAL = "PARTIAL", "Partial recovery"
        FAILED = "FAILED", "Failed"
        STALE = "STALE", "Stale"

    domain_name = models.CharField(max_length=253, db_index=True)
    baseline_snapshot = models.ForeignKey(
        DomainSnapshot,
        on_delete=models.PROTECT,
        related_name="recovery_plans",
    )
    incident = models.ForeignKey(
        Incident,
        on_delete=models.PROTECT,
        related_name="recovery_plans",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PREVIEW)
    live_fingerprint_before = models.CharField(max_length=64)
    target_fingerprint = models.CharField(max_length=64)
    plan_fingerprint = models.CharField(max_length=64, db_index=True)
    operations = models.JSONField(default=list)
    operation_results = models.JSONField(default=list)
    verification = models.JSONField(default=dict)
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class RecoveryAuditEvent(models.Model):
    plan = models.ForeignKey(
        RecoveryPlan,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    sequence = models.PositiveIntegerField()
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "sequence"],
                name="unique_recovery_audit_sequence",
            )
        ]


class IncidentExplanation(models.Model):
    class Status(models.TextChoices):
        GENERATED = "GENERATED", "Generated"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"
        INVALID = "INVALID", "Invalid provider output"

    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="ai_explanations",
    )
    evidence_fingerprint = models.CharField(max_length=64, db_index=True)
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=96, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    analysis = models.JSONField(default=dict)
    evidence_catalog = models.JSONField(default=list)
    request_id = models.CharField(max_length=128, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["incident", "evidence_fingerprint", "provider", "model"],
                name="unique_incident_ai_explanation",
            )
        ]


class EmergencyDomainPlan(models.Model):
    class Status(models.TextChoices):
        PREVIEW = "PREVIEW", "Preview"
        APPROVED = "APPROVED", "Approved"
        APPLYING = "APPLYING", "Applying"
        READY = "READY", "Emergency domain ready"
        PARTIAL = "PARTIAL", "Partial clone"
        FAILED = "FAILED", "Failed"
        STALE = "STALE", "Availability changed"

    source_domain_name = models.CharField(max_length=253, db_index=True)
    target_domain_name = models.CharField(max_length=253, db_index=True)
    baseline_snapshot = models.ForeignKey(
        DomainSnapshot,
        on_delete=models.PROTECT,
        related_name="emergency_domain_plans",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PREVIEW)
    availability = models.JSONField(default=dict)
    registration = models.JSONField(default=dict)
    expected_fingerprint = models.CharField(max_length=64)
    actual_fingerprint = models.CharField(max_length=64, blank=True)
    plan_fingerprint = models.CharField(max_length=64, db_index=True)
    idempotency_key = models.CharField(max_length=64, unique=True)
    operations = models.JSONField(default=list)
    operation_results = models.JSONField(default=list)
    verification = models.JSONField(default=dict)
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class EmergencyDomainAuditEvent(models.Model):
    plan = models.ForeignKey(
        EmergencyDomainPlan,
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    sequence = models.PositiveIntegerField()
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "sequence"],
                name="unique_emergency_domain_audit_sequence",
            )
        ]
