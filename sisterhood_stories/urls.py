from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from .views import explore, home
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse


def health_check(request):
    return HttpResponse('ok', content_type='text/plain')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('', home, name='home'),
    path('explore/', explore, name='explore'),
    path('accounts/', include('accounts.urls')),
    path('stories/', include('stories.urls')),
    path('community/', include('community.urls')),
    path('counseling/', include('counseling.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('moderation/', include('moderation.urls')),
    # Temporarily disabled APIs
    path('api/', lambda request: HttpResponse('API is temporarily disabled', status=503)),
    path('api/counseling/', lambda request: HttpResponse('Counseling API is temporarily disabled', status=503)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
