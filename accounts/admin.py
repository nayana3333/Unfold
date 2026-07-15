from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'verification_status', 'created_at', 'updated_at')
    list_filter = ('role', 'verification_status', 'created_at')
    search_fields = ('user__username', 'user__email', 'bio', 'interests')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('approve_counselors', 'reject_counselors')

    @admin.action(description='Approve selected counselor profiles')
    def approve_counselors(self, request, queryset):
        queryset.filter(role=Profile.ROLE_COUNSELOR).update(
            verification_status=Profile.VERIFICATION_APPROVED
        )

    @admin.action(description='Reject selected counselor profiles')
    def reject_counselors(self, request, queryset):
        queryset.filter(role=Profile.ROLE_COUNSELOR).update(
            verification_status=Profile.VERIFICATION_REJECTED
        )
