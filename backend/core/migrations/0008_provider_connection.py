from django.db import migrations, models
import django.db.models.deletion


def seed_existing_namecom_connections(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    ProviderConnection = apps.get_model("core", "ProviderConnection")
    for organization in Organization.objects.all().iterator():
        ProviderConnection.objects.get_or_create(
            organization=organization,
            provider="name.com",
            defaults={"is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_managed_domain"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("name.com", "name.com")], max_length=32)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_connections",
                        to="core.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["organization_id", "provider"],
                "indexes": [
                    models.Index(
                        fields=["organization", "provider", "is_active"],
                        name="provider_conn_org_active_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organization", "provider"),
                        name="unique_provider_connection_org_provider",
                    )
                ],
            },
        ),
        migrations.RunPython(seed_existing_namecom_connections, migrations.RunPython.noop),
    ]
