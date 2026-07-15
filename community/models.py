from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Group(models.Model):
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')
    cover_image = models.ImageField(upload_to='groups/covers/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def member_count(self):
        return self.members.count()
    
    def is_member(self, user):
        if not user.is_authenticated:
            return False
        return self.members.filter(user=user).exists()
    
    def is_creator(self, user):
        return self.creator == user


class GroupMember(models.Model):
    ROLE_CHOICES = (
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    )
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('group', 'user')
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class Discussion(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='discussions')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions')
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
    
    def __str__(self):
        return f"{self.title or 'Discussion'} in {self.group.name}"
    
    def comment_count(self):
        return self.comments.count()
    
    def like_count(self):
        return self.likes.count()
    
    def is_liked_by(self, user):
        if not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()

    def can_manage(self, user):
        if not user.is_authenticated:
            return False
        if user.is_staff or self.author_id == user.id or self.group.creator_id == user.id:
            return True
        return self.group.members.filter(user=user, role__in=["admin", "moderator"]).exists()


class DiscussionLike(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussion_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('discussion', 'user')
    
    def __str__(self):
        return f"{self.user.username} likes {self.discussion}"


class Comment(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.discussion}"
