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
