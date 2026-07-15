from django.urls import path

from . import views

app_name = 'moderation'

urlpatterns = [
    path('', views.ModerationDashboardView.as_view(), name='dashboard'),
    path('report/<str:app_label>/<str:model_name>/<int:object_id>/', views.CreateReportView.as_view(), name='create_report'),
    path('reports/<int:pk>/<str:status>/', views.UpdateReportStatusView.as_view(), name='update_report'),
    path('counselors/<int:pk>/<str:status>/', views.UpdateCounselorStatusView.as_view(), name='update_counselor'),
]
