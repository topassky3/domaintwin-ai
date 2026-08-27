from django.urls import path

from .ai_views import incident_explanation
from .auth_views import auth_csrf, auth_login, auth_logout, auth_me
from .emergency_views import (
    emergency_check,
    emergency_plan_apply,
    emergency_plan_approve,
    emergency_plan_detail,
    emergency_plans,
    emergency_search,
    emergency_status,
)
from .monitor_views import (
    domain_health,
    domain_incidents,
    domain_monitor_status,
    evaluate_domain,
    incident_detail,
)
from .recovery_views import (
    domain_recovery_plans,
    recovery_plan_apply,
    recovery_plan_approve,
    recovery_plan_detail,
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
    path("auth/csrf/", auth_csrf, name="auth-csrf"),
    path("auth/login/", auth_login, name="auth-login"),
    path("auth/logout/", auth_logout, name="auth-logout"),
    path("auth/me/", auth_me, name="auth-me"),
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
    path(
        "ai/incidents/<int:incident_id>/explanation/",
        incident_explanation,
        name="incident-ai-explanation",
    ),
    path(
        "recovery/domains/<str:domain_name>/plans/",
        domain_recovery_plans,
        name="domain-recovery-plans",
    ),
    path(
        "recovery/plans/<int:plan_id>/",
        recovery_plan_detail,
        name="recovery-plan-detail",
    ),
    path(
        "recovery/plans/<int:plan_id>/approve/",
        recovery_plan_approve,
        name="recovery-plan-approve",
    ),
    path(
        "recovery/plans/<int:plan_id>/apply/",
        recovery_plan_apply,
        name="recovery-plan-apply",
    ),
    path("emergency/status/", emergency_status, name="emergency-status"),
    path("emergency/search/", emergency_search, name="emergency-search"),
    path("emergency/check/", emergency_check, name="emergency-check"),
    path(
        "emergency/domains/<str:source_domain>/plans/",
        emergency_plans,
        name="emergency-plans",
    ),
    path(
        "emergency/plans/<int:plan_id>/",
        emergency_plan_detail,
        name="emergency-plan-detail",
    ),
    path(
        "emergency/plans/<int:plan_id>/approve/",
        emergency_plan_approve,
        name="emergency-plan-approve",
    ),
    path(
        "emergency/plans/<int:plan_id>/apply/",
        emergency_plan_apply,
        name="emergency-plan-apply",
    ),
]
