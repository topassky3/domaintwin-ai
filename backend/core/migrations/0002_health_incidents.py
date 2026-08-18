from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HealthObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain_name", models.CharField(db_index=True, max_length=253)),
                ("dns_resolution", models.JSONField(default=dict)),
                ("http", models.JSONField(default=dict)),
                ("https", models.JSONField(default=dict)),
                ("availability_ok", models.BooleanField()),
                ("checked_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-checked_at", "-id"]},
        ),
        migrations.CreateModel(
            name="Incident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain_name", models.CharField(db_index=True, max_length=253)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("RESOLVED", "Resolved")], default="OPEN", max_length=16)),
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("severity", models.CharField(default="LOW", max_length=16)),
                ("factors", models.JSONField(default=list)),
                ("evidence", models.JSONField(default=dict)),
                ("evidence_fingerprint", models.CharField(max_length=64)),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("baseline_snapshot", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incidents", to="core.domainsnapshot")),
            ],
            options={"ordering": ["-opened_at", "-id"]},
        ),
        migrations.CreateModel(
            name="IncidentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveIntegerField()),
                ("event_type", models.CharField(max_length=64)),
                ("payload", models.JSONField(default=dict)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("incident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="timeline", to="core.incident")),
            ],
            options={"ordering": ["sequence", "id"]},
        ),
        migrations.AddConstraint(
            model_name="incident",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "OPEN")), fields=("domain_name",), name="unique_open_incident_per_domain"),
        ),
        migrations.AddConstraint(
            model_name="incidentevent",
            constraint=models.UniqueConstraint(fields=("incident", "sequence"), name="unique_incident_event_sequence"),
        ),
    ]
