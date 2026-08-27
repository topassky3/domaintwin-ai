from django.contrib import admin

from .models import ManagedDomain, Membership, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("user__username", "user__email", "organization__name", "organization__slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ManagedDomain)
class ManagedDomainAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "organization")
    search_fields = ("name", "organization__name", "organization__slug")
    readonly_fields = ("id", "created_at", "updated_at")
