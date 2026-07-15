from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from .models import PsychiatristProfile, AvailabilitySlot, Booking
from .serializers import (
    PsychiatristProfileSerializer,
    AvailabilitySlotSerializer,
    BookingSerializer,
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "user", None)
        return owner == request.user


class PsychiatristProfileViewSet(viewsets.ModelViewSet):
    queryset = PsychiatristProfile.objects.all().order_by("-created_at")
    serializer_class = PsychiatristProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_female=True)


class AvailabilitySlotViewSet(viewsets.ModelViewSet):
    queryset = AvailabilitySlot.objects.select_related("psychiatrist").all()
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        psychiatrist_id = self.request.query_params.get("psychiatrist")
        if psychiatrist_id:
            qs = qs.filter(psychiatrist_id=psychiatrist_id)
        return qs


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related("psychiatrist", "slot", "user").all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        # Users see their own bookings; staff can see all
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        slot = serializer.validated_data["slot"]
        if slot.is_booked or slot.start <= timezone.now():
            raise ValueError("Slot is not available for booking.")
        slot.is_booked = True
        slot.save(update_fields=["is_booked"])
        serializer.save(user=self.request.user, status="confirmed")

    @action(detail=True, methods=["post"]) 
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.user != request.user and not request.user.is_staff:
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        booking.status = "cancelled"
        booking.slot.is_booked = False
        booking.slot.save(update_fields=["is_booked"])
        booking.save(update_fields=["status"])
        return Response({"status": "cancelled"})
