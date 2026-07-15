from rest_framework.routers import DefaultRouter
from .api_views import PsychiatristProfileViewSet, AvailabilitySlotViewSet, BookingViewSet

router = DefaultRouter()
router.register(r"psychiatrists", PsychiatristProfileViewSet, basename="psychiatrists")
router.register(r"slots", AvailabilitySlotViewSet, basename="slots")
router.register(r"bookings", BookingViewSet, basename="bookings")

urlpatterns = router.urls
