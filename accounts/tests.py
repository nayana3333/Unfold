from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import RegisterForm
from .models import Profile


class ProfileSignalTests(TestCase):
    def test_profile_is_created_for_new_user(self):
        user = User.objects.create_user(username='nayana', password='StrongPass123!')

        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.role, Profile.ROLE_PATIENT)


class RegisterFormTests(TestCase):
    def test_patient_registration_sets_approved_patient_role(self):
        form = RegisterForm(
            data={
                'username': 'patient_user',
                'email': 'patient@example.com',
                'role': Profile.ROLE_PATIENT,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        user.refresh_from_db()

        self.assertEqual(user.profile.role, Profile.ROLE_PATIENT)
        self.assertEqual(user.profile.verification_status, Profile.VERIFICATION_APPROVED)

    def test_counselor_registration_starts_pending_verification(self):
        form = RegisterForm(
            data={
                'username': 'counselor_user',
                'email': 'counselor@example.com',
                'role': Profile.ROLE_COUNSELOR,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        user.refresh_from_db()

        self.assertEqual(user.profile.role, Profile.ROLE_COUNSELOR)
        self.assertEqual(user.profile.verification_status, Profile.VERIFICATION_PENDING)


class RegisterViewTests(TestCase):
    def test_register_page_exposes_role_selection(self):
        response = self.client.get(reverse('accounts:register'))

        self.assertContains(response, 'I am registering as')
        self.assertContains(response, 'Counselor')


class ProfilePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='nayana',
            email='nayana@example.com',
            password='StrongPass123!',
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_page_renders_social_sections(self):
        self.client.login(username='nayana', password='StrongPass123!')

        response = self.client.get(reverse('accounts:profile'))

        self.assertContains(response, 'nayana')
        self.assertContains(response, 'Create something new')
        self.assertContains(response, 'Posts')
        self.assertContains(response, 'Saved')
