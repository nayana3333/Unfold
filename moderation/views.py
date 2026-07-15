from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView
from django.views.generic import TemplateView

from accounts.models import Profile
from .forms import ReportForm
from .models import ModerationAction, Report


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('accounts:login')

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, 'Only staff moderators can access that page.')
            return redirect('home')
        return super().handle_no_permission()


class CreateReportView(LoginRequiredMixin, CreateView):
    form_class = ReportForm
    template_name = 'moderation/report_form.html'
    allowed_targets = {
        ('stories', 'post'),
        ('stories', 'comment'),
        ('community', 'discussion'),
        ('community', 'comment'),
    }

    def dispatch(self, request, *args, **kwargs):
        target_key = (kwargs['app_label'], kwargs['model_name'])
        if target_key not in self.allowed_targets:
            messages.error(request, 'This content type cannot be reported.')
            return redirect('home')
        self.content_type = get_object_or_404(
            ContentType,
            app_label=kwargs['app_label'],
            model=kwargs['model_name'],
        )
        self.target = get_object_or_404(self.content_type.model_class(), pk=kwargs['object_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        duplicate = Report.objects.filter(
            reporter=self.request.user,
            content_type=self.content_type,
            object_id=self.target.pk,
        ).exclude(status__in=['resolved', 'dismissed']).first()
        if duplicate:
            messages.info(self.request, 'You already have an active report for this content.')
            return redirect(self.get_success_url())

        form.instance.reporter = self.request.user
        form.instance.content_type = self.content_type
        form.instance.object_id = self.target.pk
        response = super().form_valid(form)
        ModerationAction.objects.create(
            moderator=self.request.user,
            action='report_created',
            report=self.object,
            target_label=str(self.target)[:200],
            to_value=self.object.status,
            note=self.object.details,
        )
        messages.success(self.request, 'Report submitted. A moderator will review it.')
        return response

    def get_success_url(self):
        return self.request.GET.get('next') or reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target'] = self.target
        context['target_type'] = self.content_type.model
        return context


class ModerationDashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'moderation/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status_filter = self.request.GET.get('status', '').strip()
        severity_filter = self.request.GET.get('severity', '').strip()
        reports = Report.objects.select_related('reporter', 'reviewer', 'content_type')
        if status_filter:
            reports = reports.filter(status=status_filter)
        else:
            reports = reports.exclude(status__in=['resolved', 'dismissed'])
        if severity_filter:
            reports = reports.filter(severity=severity_filter)

        context['open_reports'] = reports.select_related(
            'reporter', 'reviewer', 'content_type'
        )[:25]
        context['pending_counselors'] = Profile.objects.filter(
            role=Profile.ROLE_COUNSELOR,
            verification_status=Profile.VERIFICATION_PENDING,
        ).select_related('user')[:25]
        context['report_counts'] = {
            'open': Report.objects.filter(status='open').count(),
            'reviewing': Report.objects.filter(status='reviewing').count(),
            'critical': Report.objects.filter(severity='critical').exclude(status__in=['resolved', 'dismissed']).count(),
            'resolved': Report.objects.filter(status='resolved').count(),
            'dismissed': Report.objects.filter(status='dismissed').count(),
        }
        context['pending_counselor_count'] = Profile.objects.filter(
            role=Profile.ROLE_COUNSELOR,
            verification_status=Profile.VERIFICATION_PENDING,
        ).count()
        context['recent_actions'] = ModerationAction.objects.select_related('moderator', 'report')[:10]
        context['selected_status'] = status_filter
        context['selected_severity'] = severity_filter
        context['status_choices'] = Report.STATUS_CHOICES
        context['severity_choices'] = Report.SEVERITY_CHOICES
        return context


class UpdateReportStatusView(StaffRequiredMixin, View):
    allowed_statuses = {'open', 'reviewing', 'resolved', 'dismissed'}

    def post(self, request, pk, status):
        if status not in self.allowed_statuses:
            messages.error(request, 'Invalid report status.')
            return redirect(reverse_lazy('moderation:dashboard'))

        report = get_object_or_404(Report, pk=pk)
        old_status = report.status
        report.status = status
        report.reviewer = request.user
        report.resolution_note = request.POST.get('resolution_note', report.resolution_note)
        report.save(update_fields=['status', 'reviewer', 'resolution_note', 'updated_at'])
        ModerationAction.objects.create(
            moderator=request.user,
            action='report_status',
            report=report,
            target_label=str(report.target)[:200],
            from_value=old_status,
            to_value=status,
            note=report.resolution_note,
        )
        messages.success(request, f'Report #{report.pk} marked as {status}.')
        return redirect(reverse_lazy('moderation:dashboard'))


class UpdateCounselorStatusView(StaffRequiredMixin, View):
    allowed_statuses = {
        Profile.VERIFICATION_APPROVED,
        Profile.VERIFICATION_REJECTED,
        Profile.VERIFICATION_PENDING,
    }

    def post(self, request, pk, status):
        if status not in self.allowed_statuses:
            messages.error(request, 'Invalid counselor verification status.')
            return redirect(reverse_lazy('moderation:dashboard'))

        profile = get_object_or_404(Profile, pk=pk, role=Profile.ROLE_COUNSELOR)
        old_status = profile.verification_status
        profile.verification_status = status
        profile.save(update_fields=['verification_status', 'updated_at'])
        ModerationAction.objects.create(
            moderator=request.user,
            action='counselor_status',
            target_label=profile.user.username,
            from_value=old_status,
            to_value=status,
            note=request.POST.get('note', ''),
        )
        messages.success(request, f'{profile.user.username} marked as {status}.')
        return redirect(reverse_lazy('moderation:dashboard'))
