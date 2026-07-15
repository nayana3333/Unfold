from django.urls import path
from . import views
from .views_dashboard import CounselorDashboardView

app_name = 'counseling'

urlpatterns = [
    path('', views.CounselingListView.as_view(), name='list'),
    path('dashboard/', CounselorDashboardView.as_view(), name='dashboard'),
    path('patient-dashboard/', views.PatientDashboardView.as_view(), name='patient_dashboard'),
    path('psychiatrist-dashboard/', views.PsychiatristDashboardView.as_view(), name='psychiatrist_dashboard'),
    path('book/<int:psychiatrist_id>/', views.BookAppointmentView.as_view(), name='book_appointment'),
    path('booking/<int:booking_id>/<str:status>/', views.UpdateBookingStatusView.as_view(), name='update_booking_status'),
    path('session/<int:booking_id>/', views.SessionView.as_view(), name='session'),
    path('feedback/<int:booking_id>/', views.SubmitFeedbackView.as_view(), name='feedback'),
    path('directory/', views.BrowseDirectoryView.as_view(), name='directory'),
]
