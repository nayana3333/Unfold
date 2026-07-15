from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.shortcuts import redirect
from .models import PsychiatristProfile, AvailabilitySlot, Booking

class CounselorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "counseling/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = PsychiatristProfile.objects.filter(user=self.request.user).first()
        slots = AvailabilitySlot.objects.filter(psychiatrist=profile).order_by("start") if profile else []
        bookings = Booking.objects.filter(psychiatrist=profile).select_related("user", "slot").order_by("-created_at") if profile else []
        ctx.update({
            "profile": profile,
            "slots": slots,
            "bookings": bookings,
        })
        return ctx
