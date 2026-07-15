from django.urls import path
from .views import CustomLoginView, CustomLogoutView, RegisterView, ProfileView, DeleteAccountView

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('login/patient/', CustomLoginView.as_view(template_name='accounts/login_patient.html'), name='login_patient'),
    path('login/counselor/', CustomLoginView.as_view(template_name='accounts/login_counselor.html'), name='login_counselor'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),
]
