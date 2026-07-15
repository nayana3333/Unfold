from django.contrib import admin
from .models import PsychiatristProfile, AvailabilitySlot, Booking, Feedback


@admin.register(PsychiatristProfile)
class PsychiatristProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "license_no", "specialization", "years_experience", "is_verified")
    list_filter = ("is_verified", "specialization")
    search_fields = ("full_name", "license_no", "languages")


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("psychiatrist", "start", "end", "is_booked")
    list_filter = ("is_booked",)
    search_fields = ("psychiatrist__full_name",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("user", "psychiatrist", "mode", "status", "created_at")
    list_filter = ("status", "mode")
    search_fields = ("user__username", "psychiatrist__full_name")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("booking", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("booking__psychiatrist__full_name", "comment")
