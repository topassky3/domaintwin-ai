from django.urls import path

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
]
