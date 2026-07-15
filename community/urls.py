from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    path('', views.CommunityListView.as_view(), name='list'),
    path('create/', views.CreateGroupView.as_view(), name='create_group'),
    path('group/<int:pk>/', views.GroupDetailView.as_view(), name='group_detail'),
    path('group/<int:pk>/join/', views.JoinGroupView.as_view(), name='join_group'),
    path('group/<int:pk>/leave/', views.LeaveGroupView.as_view(), name='leave_group'),
    path('group/<int:group_id>/discussion/create/', views.CreateDiscussionView.as_view(), name='create_discussion'),
    path('discussion/<int:pk>/', views.DiscussionDetailView.as_view(), name='discussion_detail'),
    path('discussion/<int:pk>/like/', views.ToggleDiscussionLikeView.as_view(), name='toggle_like'),
    path('discussion/<int:discussion_id>/comment/', views.CreateCommentView.as_view(), name='create_comment'),
    path('discussion/<int:pk>/<str:action>/', views.UpdateDiscussionView.as_view(), name='update_discussion'),
]
