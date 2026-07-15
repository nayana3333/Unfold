from django.contrib import admin
from .models import Group, GroupMember, Discussion, DiscussionLike, Comment


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'visibility', 'member_count', 'created_at', 'is_active')
    list_filter = ('visibility', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'creator__username')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('group__name', 'user__username')


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'author', 'is_pinned', 'created_at')
    list_filter = ('is_pinned', 'created_at', 'group')
    search_fields = ('title', 'content', 'group__name', 'author__username')


@admin.register(DiscussionLike)
class DiscussionLikeAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('discussion__title', 'user__username')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'discussion__title', 'author__username')
