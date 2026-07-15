from django.urls import path
from . import views

app_name = 'stories'

urlpatterns = [
    # Post URLs
    path('', views.PostListView.as_view(), name='post_list'),
    path('post/create/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<int:post_id>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/<int:post_id>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    
    # Like/comment URLs
    path('like/<int:post_id>/', views.LikeToggleView.as_view(), name='like_toggle'),
    path('save/<int:post_id>/', views.SaveToggleView.as_view(), name='save_toggle'),
    path('comment/<int:post_id>/', views.CommentCreateView.as_view(), name='comment_create'),
    
    # Story URLs
    path('stories/create/', views.StoryCreateView.as_view(), name='story_create'),
    path('stories/<int:pk>/', views.StoryDetailView.as_view(), name='story_detail'),
    path('stories/<int:story_id>/view/', views.StoryViewView.as_view(), name='story_view'),
]
