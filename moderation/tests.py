from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from stories.models import Post
from .models import ModerationAction, Report


class ModerationDashboardTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='StrongPass123!', is_staff=True)
        self.user = User.objects.create_user(username='member', password='StrongPass123!')
        self.post = Post.objects.create(author=self.user, content='Needs review')
        self.report = Report.objects.create(
            reporter=self.user,
            content_type=ContentType.objects.get_for_model(Post),
            object_id=self.post.id,
            reason='harassment',
            severity='high',
            details='Unsafe reply',
        )

    def test_dashboard_requires_staff(self):
        response = self.client.get(reverse('moderation:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_non_staff_is_redirected_from_dashboard(self):
        self.client.login(username='member', password='StrongPass123!')
        response = self.client.get(reverse('moderation:dashboard'))

        self.assertRedirects(response, reverse('home'))

    def test_staff_can_view_dashboard(self):
        self.client.login(username='staff', password='StrongPass123!')
        response = self.client.get(reverse('moderation:dashboard'))
        self.assertContains(response, 'Moderation dashboard')
        self.assertContains(response, 'Open reports')

    def test_staff_can_resolve_report(self):
        self.client.login(username='staff', password='StrongPass123!')
        response = self.client.post(
            reverse('moderation:update_report', args=[self.report.id, 'resolved']),
            {'resolution_note': 'Removed unsafe content.'},
        )
        self.assertRedirects(response, reverse('moderation:dashboard'))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'resolved')
        self.assertEqual(self.report.reviewer, self.staff)
        self.assertEqual(self.report.resolution_note, 'Removed unsafe content.')
        self.assertTrue(ModerationAction.objects.filter(report=self.report, action='report_status').exists())

    def test_staff_can_approve_pending_counselor(self):
        counselor = User.objects.create_user(username='counselor', password='StrongPass123!')
        counselor.profile.role = Profile.ROLE_COUNSELOR
        counselor.profile.verification_status = Profile.VERIFICATION_PENDING
        counselor.profile.save()

        self.client.login(username='staff', password='StrongPass123!')
        response = self.client.post(
            reverse('moderation:update_counselor', args=[counselor.profile.id, Profile.VERIFICATION_APPROVED])
        )

        self.assertRedirects(response, reverse('moderation:dashboard'))
        counselor.profile.refresh_from_db()
        self.assertEqual(counselor.profile.verification_status, Profile.VERIFICATION_APPROVED)
        self.assertTrue(
            ModerationAction.objects.filter(
                action='counselor_status',
                target_label='counselor',
                to_value=Profile.VERIFICATION_APPROVED,
            ).exists()
        )

    def test_non_staff_cannot_update_report_status(self):
        self.client.login(username='member', password='StrongPass123!')
        response = self.client.post(
            reverse('moderation:update_report', args=[self.report.id, 'resolved']),
            {'resolution_note': 'Trying to close this.'},
        )

        self.assertRedirects(response, reverse('home'))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'open')
        self.assertIsNone(self.report.reviewer)

    def test_report_form_explains_review_flow(self):
        self.client.login(username='member', password='StrongPass123!')
        response = self.client.get(reverse('moderation:create_report', args=['stories', 'post', self.post.id]))

        self.assertContains(response, 'Report content')
        self.assertContains(response, 'Reports go to staff moderation')
        self.assertContains(response, 'Reporting post')

    def test_authenticated_user_can_report_post(self):
        fresh_post = Post.objects.create(author=self.staff, content='Fresh report target')
        self.client.login(username='member', password='StrongPass123!')
        response = self.client.post(
            reverse('moderation:create_report', args=['stories', 'post', fresh_post.id]),
            {
                'reason': 'harassment',
                'severity': 'high',
                'details': 'This content is unsafe.',
            },
        )

        self.assertRedirects(response, reverse('home'))
        self.assertTrue(
            Report.objects.filter(
                reporter=self.user,
                reason='harassment',
                object_id=fresh_post.id,
            ).exists()
        )
        self.assertTrue(ModerationAction.objects.filter(action='report_created').exists())

    def test_duplicate_active_report_is_not_created(self):
        self.client.login(username='member', password='StrongPass123!')
        response = self.client.post(
            reverse('moderation:create_report', args=['stories', 'post', self.post.id]),
            {
                'reason': 'harassment',
                'severity': 'high',
                'details': 'Same content again.',
            },
        )

        self.assertRedirects(response, reverse('home'))
        self.assertEqual(
            Report.objects.filter(
                reporter=self.user,
                content_type=ContentType.objects.get_for_model(Post),
                object_id=self.post.id,
            ).count(),
            1,
        )

    def test_dashboard_filters_reports(self):
        self.report.status = 'resolved'
        self.report.save(update_fields=['status'])
        self.client.login(username='staff', password='StrongPass123!')

        response = self.client.get(reverse('moderation:dashboard'), {'status': 'resolved'})

        self.assertContains(response, '#')
        self.assertContains(response, 'Resolved')
