from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.ChatbotView.as_view(), name='chat'),
    path('api/ask/', views.chat_api, name='chat_api'),
]
