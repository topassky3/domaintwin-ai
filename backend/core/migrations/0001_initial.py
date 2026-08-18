from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DomainSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain_name", models.CharField(db_index=True, max_length=253)),
                ("version", models.PositiveIntegerField()),
                ("records", models.JSONField(default=list)),
                ("fingerprint", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["domain_name", "-version"]},
        ),
        migrations.CreateModel(
            name="KnownGoodSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain_name", models.CharField(max_length=253, unique=True)),
                ("marked_at", models.DateTimeField(auto_now=True)),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="known_good_for",
                        to="core.domainsnapshot",
                    ),
                ),
            ],
            options={"ordering": ["domain_name"]},
        ),
        migrations.AddConstraint(
            model_name="domainsnapshot",
            constraint=models.UniqueConstraint(
                fields=("domain_name", "version"),
                name="unique_domain_snapshot_version",
            ),
        ),
    ]
