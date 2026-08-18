from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_health_incidents"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecoveryPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain_name", models.CharField(db_index=True, max_length=253)),
                ("status", models.CharField(choices=[("PREVIEW", "Preview"), ("APPROVED", "Approved"), ("APPLYING", "Applying"), ("RECOVERED", "Recovered"), ("PARTIAL", "Partial recovery"), ("FAILED", "Failed"), ("STALE", "Stale")], default="PREVIEW", max_length=16)),
                ("live_fingerprint_before", models.CharField(max_length=64)),
                ("target_fingerprint", models.CharField(max_length=64)),
                ("plan_fingerprint", models.CharField(db_index=True, max_length=64)),
                ("operations", models.JSONField(default=list)),
                ("operation_results", models.JSONField(default=list)),
                ("verification", models.JSONField(default=dict)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("baseline_snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recovery_plans", to="core.domainsnapshot")),
                ("incident", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="recovery_plans", to="core.incident")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="RecoveryAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveIntegerField()),
                ("event_type", models.CharField(max_length=64)),
                ("payload", models.JSONField(default=dict)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="core.recoveryplan")),
            ],
            options={"ordering": ["sequence", "id"]},
        ),
        migrations.AddConstraint(
            model_name="recoveryplan",
            constraint=models.UniqueConstraint(fields=("domain_name", "plan_fingerprint"), name="unique_recovery_plan_fingerprint_per_domain"),
        ),
        migrations.AddConstraint(
            model_name="recoveryauditevent",
            constraint=models.UniqueConstraint(fields=("plan", "sequence"), name="unique_recovery_audit_sequence"),
        ),
    ]
