from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment, Like


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]



class CommentSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "user", "post", "text", "created_at"]
        read_only_fields = ["id", "created_at", "user"]


class LikeSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ["id", "user", "post", "created_at"]
        read_only_fields = ["id", "created_at", "user"]


class PostSerializer(serializers.ModelSerializer):
    author = UserPublicSerializer(read_only=True)
    likes_count = serializers.IntegerField(source="like_set.count", read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "content",
            "image",
            "file",
            "created_at",
            "shared_post",
            "likes_count",
        ]
        read_only_fields = ["id", "created_at", "author", "likes_count"]
