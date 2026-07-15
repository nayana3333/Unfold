from rest_framework.routers import DefaultRouter
from .api_views import StoryViewSet, PostViewSet

router = DefaultRouter()
router.register(r"stories", StoryViewSet, basename="api-stories")
router.register(r"posts", PostViewSet, basename="api-posts")

urlpatterns = router.urls
