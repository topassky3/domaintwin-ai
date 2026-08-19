from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_recovery_engine"),
    ]

    operations = [
        migrations.CreateModel(
            name="IncidentExplanation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("evidence_fingerprint", models.CharField(db_index=True, max_length=64)),
                ("provider", models.CharField(max_length=32)),
                ("model", models.CharField(blank=True, max_length=96)),
                ("status", models.CharField(choices=[("GENERATED", "Generated"), ("UNAVAILABLE", "Unavailable"), ("INVALID", "Invalid provider output")], max_length=16)),
                ("analysis", models.JSONField(default=dict)),
                ("evidence_catalog", models.JSONField(default=list)),
                ("request_id", models.CharField(blank=True, max_length=128)),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_explanations", to="core.incident")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="incidentexplanation",
            constraint=models.UniqueConstraint(
                fields=("incident", "evidence_fingerprint", "provider", "model"),
                name="unique_incident_ai_explanation",
            ),
        ),
    ]
