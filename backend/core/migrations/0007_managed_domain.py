from __future__ import annotations

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_multitenant_foundation"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManagedDomain",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=253, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="managed_domains",
                        to="core.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["organization_id", "name"],
                "indexes": [
                    models.Index(
                        fields=["organization", "is_active"],
                        name="managed_domain_org_active_idx",
                    ),
                ],
            },
        ),
    ]
