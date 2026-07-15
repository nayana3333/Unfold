from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import Post, Comment, Like
from .serializers import PostSerializer, CommentSerializer, LikeSerializer


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        author = getattr(obj, "author", None)
        return author == request.user


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related("author").order_by("-created_at")
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
            return Response({"liked": False, "likes_count": post.like_set.count()})
        return Response({"liked": True, "likes_count": post.like_set.count()})

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, pk=None):
        post = self.get_object()
        if request.method == "GET":
            qs = Comment.objects.filter(post=post).select_related("user").order_by("created_at")
            return Response(CommentSerializer(qs, many=True).data)
        # POST
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"detail": "text is required"}, status=status.HTTP_400_BAD_REQUEST)
        comment = Comment.objects.create(user=request.user, post=post, text=text)
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
