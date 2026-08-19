from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_incident_explanations"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmergencyDomainPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_domain_name", models.CharField(db_index=True, max_length=253)),
                ("target_domain_name", models.CharField(db_index=True, max_length=253)),
                ("status", models.CharField(choices=[("PREVIEW", "Preview"), ("APPROVED", "Approved"), ("APPLYING", "Applying"), ("READY", "Emergency domain ready"), ("PARTIAL", "Partial clone"), ("FAILED", "Failed"), ("STALE", "Availability changed")], default="PREVIEW", max_length=16)),
                ("availability", models.JSONField(default=dict)),
                ("registration", models.JSONField(default=dict)),
                ("expected_fingerprint", models.CharField(max_length=64)),
                ("actual_fingerprint", models.CharField(blank=True, max_length=64)),
                ("plan_fingerprint", models.CharField(db_index=True, max_length=64)),
                ("idempotency_key", models.CharField(max_length=64, unique=True)),
                ("operations", models.JSONField(default=list)),
                ("operation_results", models.JSONField(default=list)),
                ("verification", models.JSONField(default=dict)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("baseline_snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="emergency_domain_plans", to="core.domainsnapshot")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="EmergencyDomainAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveIntegerField()),
                ("event_type", models.CharField(max_length=64)),
                ("payload", models.JSONField(default=dict)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="core.emergencydomainplan")),
            ],
            options={"ordering": ["sequence", "id"]},
        ),
        migrations.AddConstraint(
            model_name="emergencydomainauditevent",
            constraint=models.UniqueConstraint(fields=("plan", "sequence"), name="unique_emergency_domain_audit_sequence"),
        ),
    ]
