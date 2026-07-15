from django.contrib import admin
from .models import Comment, Like, Post, SavedPost, Story


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'is_anonymous', 'allow_comments', 'created_at')
    list_filter = ('is_anonymous', 'allow_comments', 'created_at')
    search_fields = ('content', 'author__username', 'pseudonym')
    readonly_fields = ('created_at',)


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'story_type', 'is_anonymous', 'pseudonym', 'created_at', 'expiry')
    list_filter = ('story_type', 'is_anonymous', 'created_at', 'expiry')
    search_fields = ('content', 'user__username', 'pseudonym')
    readonly_fields = ('created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'user__username', 'post__content')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__content')


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__content')
