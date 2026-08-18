from django.urls import path

from .monitor_views import (
    domain_health,
    domain_incidents,
    domain_monitor_status,
    evaluate_domain,
    incident_detail,
)
from .risk_views import domain_risk
from .twin_views import live_diff, snapshot_detail, snapshot_known_good, snapshots
from .views import (
    health,
    namecom_domain,
    namecom_domains,
    namecom_record_detail,
    namecom_records,
    namecom_status,
)

urlpatterns = [
    path("health/", health, name="health"),
    path("namecom/status/", namecom_status, name="namecom-status"),
    path("namecom/domains/", namecom_domains, name="namecom-domains"),
    path("namecom/domains/<str:domain_name>/", namecom_domain, name="namecom-domain"),
    path("namecom/domains/<str:domain_name>/records/", namecom_records, name="namecom-records"),
    path(
        "namecom/domains/<str:domain_name>/records/<int:record_id>/",
        namecom_record_detail,
        name="namecom-record-detail",
    ),
    path(
        "twin/domains/<str:domain_name>/snapshots/",
        snapshots,
        name="twin-snapshots",
    ),
    path(
        "twin/domains/<str:domain_name>/snapshots/<int:snapshot_id>/",
        snapshot_detail,
        name="twin-snapshot-detail",
    ),
    path(
        "twin/domains/<str:domain_name>/snapshots/<int:snapshot_id>/known-good/",
        snapshot_known_good,
        name="twin-snapshot-known-good",
    ),
    path(
        "twin/domains/<str:domain_name>/diff/",
        live_diff,
        name="twin-live-diff",
    ),
    path(
        "risk/domains/<str:domain_name>/",
        domain_risk,
        name="domain-risk",
    ),
    path(
        "monitor/domains/<str:domain_name>/health/",
        domain_health,
        name="domain-health",
    ),
    path(
        "monitor/domains/<str:domain_name>/evaluate/",
        evaluate_domain,
        name="domain-monitor-evaluate",
    ),
    path(
        "monitor/domains/<str:domain_name>/status/",
        domain_monitor_status,
        name="domain-monitor-status",
    ),
    path(
        "incidents/domains/<str:domain_name>/",
        domain_incidents,
        name="domain-incidents",
    ),
    path(
        "incidents/<int:incident_id>/",
        incident_detail,
        name="incident-detail",
    ),
]
