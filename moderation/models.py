from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Report(models.Model):
    REASON_CHOICES = (
        ('harassment', 'Harassment or bullying'),
        ('hate', 'Hate or abuse'),
        ('self_harm', 'Self-harm or crisis risk'),
        ('spam', 'Spam or misleading'),
        ('privacy', 'Privacy concern'),
        ('other', 'Other'),
    )
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('reviewing', 'Reviewing'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    )
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_reports')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_reason_display()} report #{self.pk}"


class ModerationAction(models.Model):
    ACTION_CHOICES = (
        ('report_created', 'Report created'),
        ('report_status', 'Report status changed'),
        ('counselor_status', 'Counselor verification changed'),
    )

    moderator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='moderation_actions')
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, null=True, blank=True, related_name='actions')
    target_label = models.CharField(max_length=200, blank=True)
    from_value = models.CharField(max_length=60, blank=True)
    to_value = models.CharField(max_length=60, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} -> {self.to_value or self.target_label}"
