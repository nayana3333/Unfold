from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from .models import Post, Like, Comment
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class PostListView(View):
    def get(self, request):
        posts = Post.objects.all().order_by('-created_at')
        return render(request, 'stories/post_list.html', {'posts': posts})

@method_decorator(login_required, name='dispatch')
class LikeToggleView(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
        return redirect('stories:post_list')

@method_decorator(login_required, name='dispatch')
class CommentCreateView(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        text = request.POST.get('comment_text')
        if text:
            Comment.objects.create(user=request.user, post=post, text=text)
        return redirect('stories:post_list')
