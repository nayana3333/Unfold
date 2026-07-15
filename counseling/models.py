from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class PsychiatristProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="psychiatrist_profile")
    full_name = models.CharField(max_length=120)
    license_no = models.CharField(max_length=80, unique=True)
    specialization = models.CharField(max_length=120, blank=True)  # e.g. Trauma, Depression, PTSD
    languages = models.CharField(max_length=200, blank=True)  # comma-separated list
    years_experience = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="psychiatrists/photos/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_female = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, help_text="Private average rating (optional)")
    available_chat = models.BooleanField(default=True)
    available_voice = models.BooleanField(default=True)
    available_video = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({'Verified' if self.is_verified else 'Unverified'})"

    def clean(self):
        # enforce female-only psychiatrists policy
        if not self.is_female:
            raise ValidationError("Only female psychiatrists are allowed on this platform.")


class AvailabilitySlot(models.Model):
    psychiatrist = models.ForeignKey(PsychiatristProfile, on_delete=models.CASCADE, related_name="slots")
    start = models.DateTimeField()
    end = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start"]
        unique_together = ("psychiatrist", "start", "end")

    def __str__(self):
        return f"{self.psychiatrist.full_name}: {self.start} - {self.end} {'(booked)' if self.is_booked else ''}"

    def clean(self):
        if self.end <= self.start:
            raise ValidationError("Slot end time must be after start time.")


class Booking(models.Model):
    MODE_CHOICES = (
        ("chat", "Chat"),
        ("voice", "Voice"),
        ("video", "Video"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="counseling_bookings")
    psychiatrist = models.ForeignKey(PsychiatristProfile, on_delete=models.CASCADE, related_name="bookings")
    slot = models.OneToOneField(AvailabilitySlot, on_delete=models.PROTECT, related_name="booking")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="chat")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    allow_anonymous = models.BooleanField(default=False)
    pseudonym = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.pseudonym if self.allow_anonymous and self.pseudonym else self.user.username
        return f"Booking by {who} with {self.psychiatrist.full_name} @ {self.slot.start} [{self.mode}]"

    def clean(self):
        if not self.psychiatrist_id or not self.slot_id:
            return
        # ensure psychiatrist is female and verified for safety
        if not (self.psychiatrist.is_female and self.psychiatrist.is_verified):
            raise ValidationError("Bookings are allowed only with verified female psychiatrists.")
        # ensure slot belongs to psychiatrist
        if self.slot.psychiatrist_id != self.psychiatrist_id:
            raise ValidationError("Selected slot does not belong to the chosen psychiatrist.")
        # ensure mode is supported by psychiatrist
        if self.mode == "chat" and not self.psychiatrist.available_chat:
            raise ValidationError("Psychiatrist does not accept chat sessions.")
        if self.mode == "voice" and not self.psychiatrist.available_voice:
            raise ValidationError("Psychiatrist does not accept voice sessions.")
        if self.mode == "video" and not self.psychiatrist.available_video:
            raise ValidationError("Psychiatrist does not accept video sessions.")


class Feedback(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="feedback")
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating from 1 to 5")
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Feedback for {self.booking.psychiatrist.full_name} - {self.rating}/5"
