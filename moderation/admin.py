from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reason', 'severity', 'status', 'reporter', 'reviewer', 'created_at')
    list_filter = ('reason', 'severity', 'status', 'created_at')
    search_fields = ('details', 'resolution_note', 'reporter__username', 'reviewer__username')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('mark_reviewing', 'mark_resolved', 'mark_dismissed')

    @admin.action(description='Mark selected reports as reviewing')
    def mark_reviewing(self, request, queryset):
        queryset.update(status='reviewing', reviewer=request.user)

    @admin.action(description='Mark selected reports as resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved', reviewer=request.user)

    @admin.action(description='Mark selected reports as dismissed')
    def mark_dismissed(self, request, queryset):
        queryset.update(status='dismissed', reviewer=request.user)
