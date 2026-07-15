from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import BookingForm
from .models import AvailabilitySlot, Booking, PsychiatristProfile


class CounselingBookingTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(username="patient", password="pass12345")
        self.counselor_user = User.objects.create_user(username="counselor", password="pass12345")
        self.counselor = PsychiatristProfile.objects.create(
            user=self.counselor_user,
            full_name="Ananya Rao",
            license_no="LIC-100",
            specialization="Anxiety and stress",
            years_experience=6,
            is_verified=True,
            is_female=True,
            available_chat=True,
            available_voice=False,
            available_video=True,
        )
        self.slot = AvailabilitySlot.objects.create(
            psychiatrist=self.counselor,
            start=timezone.now() + timedelta(days=1),
            end=timezone.now() + timedelta(days=1, minutes=45),
        )

    def test_booking_form_only_shows_supported_modes(self):
        form = BookingForm(psychiatrist=self.counselor)
        self.assertEqual([choice[0] for choice in form.fields["mode"].choices], ["chat", "video"])

    def test_patient_can_book_open_verified_slot(self):
        self.client.login(username="patient", password="pass12345")
        response = self.client.post(
            reverse("counseling:book_appointment", args=[self.counselor.id]),
            {
                "slot_id": self.slot.id,
                "mode": "chat",
                "notes": "I want to discuss exam stress.",
            },
        )

        self.assertRedirects(response, reverse("counseling:patient_dashboard"))
        booking = Booking.objects.get(user=self.patient)
        self.assertEqual(booking.status, "pending")
        self.slot.refresh_from_db()
        self.assertTrue(self.slot.is_booked)

    def test_counselor_can_confirm_booking(self):
        booking = Booking.objects.create(
            user=self.patient,
            psychiatrist=self.counselor,
            slot=self.slot,
            mode="chat",
            status="pending",
        )
        self.slot.is_booked = True
        self.slot.save(update_fields=["is_booked"])

        self.client.login(username="counselor", password="pass12345")
        response = self.client.post(reverse("counseling:update_booking_status", args=[booking.id, "confirmed"]))

        self.assertRedirects(response, reverse("counseling:psychiatrist_dashboard"))
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")

    def test_patient_can_cancel_and_release_slot(self):
        booking = Booking.objects.create(
            user=self.patient,
            psychiatrist=self.counselor,
            slot=self.slot,
            mode="chat",
            status="confirmed",
        )
        self.slot.is_booked = True
        self.slot.save(update_fields=["is_booked"])

        self.client.login(username="patient", password="pass12345")
        response = self.client.post(reverse("counseling:update_booking_status", args=[booking.id, "cancelled"]))

        self.assertRedirects(response, reverse("counseling:patient_dashboard"))
        booking.refresh_from_db()
        self.slot.refresh_from_db()
        self.assertEqual(booking.status, "cancelled")
        self.assertFalse(self.slot.is_booked)

    def test_unverified_counselor_cannot_be_booked_from_url(self):
        unverified_user = User.objects.create_user(username="unverified", password="pass12345")
        unverified = PsychiatristProfile.objects.create(
            user=unverified_user,
            full_name="Unverified Counselor",
            license_no="LIC-404",
            specialization="Stress",
            years_experience=2,
            is_verified=False,
            is_female=True,
        )
        AvailabilitySlot.objects.create(
            psychiatrist=unverified,
            start=timezone.now() + timedelta(days=2),
            end=timezone.now() + timedelta(days=2, minutes=45),
        )

        self.client.login(username="patient", password="pass12345")
        response = self.client.get(reverse("counseling:book_appointment", args=[unverified.id]))

        self.assertEqual(response.status_code, 404)

    def test_booking_model_rejects_unverified_counselor(self):
        unverified_user = User.objects.create_user(username="pending_doc", password="pass12345")
        unverified = PsychiatristProfile.objects.create(
            user=unverified_user,
            full_name="Pending Counselor",
            license_no="LIC-405",
            specialization="Wellness",
            years_experience=3,
            is_verified=False,
            is_female=True,
        )
        slot = AvailabilitySlot.objects.create(
            psychiatrist=unverified,
            start=timezone.now() + timedelta(days=3),
            end=timezone.now() + timedelta(days=3, minutes=45),
        )
        booking = Booking(
            user=self.patient,
            psychiatrist=unverified,
            slot=slot,
            mode="chat",
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_other_user_cannot_cancel_someone_else_booking(self):
        other = User.objects.create_user(username="other", password="pass12345")
        booking = Booking.objects.create(
            user=self.patient,
            psychiatrist=self.counselor,
            slot=self.slot,
            mode="chat",
            status="confirmed",
        )
        self.slot.is_booked = True
        self.slot.save(update_fields=["is_booked"])

        self.client.login(username="other", password="pass12345")
        response = self.client.post(reverse("counseling:update_booking_status", args=[booking.id, "cancelled"]))

        self.assertRedirects(response, reverse("counseling:patient_dashboard"))
        booking.refresh_from_db()
        self.slot.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")
        self.assertTrue(self.slot.is_booked)
