from django.views.generic import ListView, CreateView, View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.contrib import messages
from .models import Post, PostImage, Comment, Like, SavedPost, Story
from .forms import PostForm, StoryForm

User = get_user_model()


class PostListView(ListView):
    model = Post
    template_name = 'stories/post_list.html'
    context_object_name = 'posts'
    ordering = ['-created_at']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            post_ids = [p.id for p in context['posts']]
            liked = Like.objects.filter(user=self.request.user, post_id__in=post_ids).values_list('post_id', flat=True)
            context['liked_post_ids'] = list(liked)
            context['active_stories'] = Story.objects.filter(
                expiry__gt=timezone.now()
            ).exclude(
                views=self.request.user
            ).select_related('user').order_by('-created_at')
        else:
            context['liked_post_ids'] = []
            context['active_stories'] = []
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'stories/post_form.html'
    form_class = PostForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.author = self.request.user
        if not form.cleaned_data.get('is_anonymous'):
            form.instance.pseudonym = ''
        else:
            form.instance.pseudonym = form.cleaned_data.get('pseudonym', '').strip()

        response = super().form_valid(form)
        for index, image in enumerate(self.request.FILES.getlist('images')):
            PostImage.objects.create(post=self.object, image=image, position=index)
        messages.success(self.request, 'Your post has been created successfully!')
        return response


class PostDetailView(DetailView):
    model = Post
    template_name = 'stories/post_detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        return Post.objects.select_related('author').prefetch_related('comment_set__user', 'like_set', 'carousel_images')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        context['comments'] = post.comment_set.select_related('user').order_by('created_at')
        context['liked'] = self.request.user.is_authenticated and Like.objects.filter(user=self.request.user, post=post).exists()
        context['saved'] = self.request.user.is_authenticated and SavedPost.objects.filter(user=self.request.user, post=post).exists()
        return context


@method_decorator(login_required, name='dispatch')
class LikeToggleView(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'liked': created,
                'likes_count': post.like_set.count(),
                'post_id': post.id,
            })
        return redirect('stories:post_list')


@method_decorator(login_required, name='dispatch')
class SaveToggleView(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        saved, created = SavedPost.objects.get_or_create(user=request.user, post=post)
        if not created:
            saved.delete()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'saved': created,
                'saved_count': SavedPost.objects.filter(post=post).count(),
                'post_id': post.id,
            })
        return redirect('home')


@method_decorator(login_required, name='dispatch')
class PostDeleteView(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if not (post.author_id == request.user.id or request.user.is_staff):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)
            return redirect('stories:post_list')
        post.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'post_id': post_id})
        return redirect('stories:post_list')


@method_decorator(login_required, name='dispatch')
class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if not post.allow_comments:
            return JsonResponse({'status': 'error', 'message': 'Comments are disabled for this post'}, status=400)

        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({'status': 'error', 'message': 'Comment cannot be empty'}, status=400)

        comment = Comment.objects.create(
            user=request.user,
            post=post,
            text=text
        )
        html = render_to_string('stories/partials/comment.html', {'comment': comment})

        return JsonResponse({
            'status': 'success',
            'html': html,
            'comment_count': post.comment_set.count()
        })


class StoryCreateView(LoginRequiredMixin, CreateView):
    model = Story
    form_class = StoryForm
    template_name = 'stories/story_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.user = self.request.user

        if form.cleaned_data.get('image'):
            form.instance.story_type = 'image'
        elif form.cleaned_data.get('video'):
            form.instance.story_type = 'video'
        else:
            form.instance.story_type = 'text'
        if not form.cleaned_data.get('is_anonymous'):
            form.instance.pseudonym = ''
        else:
            form.instance.pseudonym = (form.cleaned_data.get('pseudonym') or '').strip()

        response = super().form_valid(form)
        messages.success(self.request, 'Your story has been posted successfully!')
        return response


class StoryViewView(LoginRequiredMixin, View):
    def post(self, request, story_id):
        story = get_object_or_404(Story, id=story_id)

        if not story.views.filter(id=request.user.id).exists():
            story.views.add(request.user)

        return JsonResponse({'status': 'success'})


class StoryDetailView(LoginRequiredMixin, DetailView):
    model = Story
    template_name = 'stories/story_detail.html'
    context_object_name = 'story'

    def get_queryset(self):
        return Story.objects.filter(expiry__gt=timezone.now())

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            fallback = Story.objects.filter(expiry__gt=timezone.now()).order_by('-created_at').first()
            if fallback:
                return redirect('stories:story_detail', pk=fallback.pk)
            messages.info(request, 'No active stories are available yet.')
            return redirect('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        story = self.get_object()

        if not story.views.filter(id=self.request.user.id).exists():
            story.views.add(self.request.user)

        context['user_stories'] = Story.objects.filter(
            user=story.user,
            expiry__gt=timezone.now()
        ).exclude(id=story.id).order_by('created_at')
        active_stories = Story.objects.filter(expiry__gt=timezone.now()).order_by('created_at')
        context['prev_story'] = active_stories.filter(created_at__lt=story.created_at).last()
        context['next_story'] = active_stories.filter(created_at__gt=story.created_at).first()

        return context
