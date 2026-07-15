from rest_framework import serializers
from django.contrib.auth.models import User
from .models import PsychiatristProfile, AvailabilitySlot, Booking


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class PsychiatristProfileSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = PsychiatristProfile
        fields = [
            "id",
            "user",
            "full_name",
            "license_no",
            "specialization",
            "languages",
            "years_experience",
            "bio",
            "photo",
            "is_verified",
            "is_female",
            "available_chat",
            "available_voice",
            "available_video",
            "created_at",
        ]
        read_only_fields = ["id", "user", "is_female", "created_at"]


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    psychiatrist = serializers.PrimaryKeyRelatedField(queryset=PsychiatristProfile.objects.all())

    class Meta:
        model = AvailabilitySlot
        fields = ["id", "psychiatrist", "start", "end", "is_booked", "created_at"]
        read_only_fields = ["id", "is_booked", "created_at"]


class BookingSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "psychiatrist",
            "slot",
            "mode",
            "status",
            "allow_anonymous",
            "pseudonym",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at"]
