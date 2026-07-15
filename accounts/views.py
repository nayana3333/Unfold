from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.db.models import Count
from stories.models import Comment as StoryComment, Like, Post, SavedPost, Story
from community.models import GroupMember
from .forms import RegisterForm
from .models import Profile

User = get_user_model()

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    
    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        return super().form_valid(form)

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('home')
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)

class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        messages.success(self.request, 'Account created successfully! Please login to continue.')
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'

    def get(self, request, *args, **kwargs):
        from django.shortcuts import render
        my_posts = Post.objects.filter(author=request.user).prefetch_related('carousel_images').order_by('-created_at')
        my_stories = Story.objects.filter(user=request.user).order_by('-created_at')
        my_comments = StoryComment.objects.filter(user=request.user).select_related('post', 'post__author').order_by('-created_at')
        my_memberships = GroupMember.objects.filter(user=request.user).select_related('group').order_by('-joined_at')
        saved_posts = SavedPost.objects.filter(user=request.user).select_related('post', 'post__author').prefetch_related('post__carousel_images').order_by('-created_at')
        post_likes_received = Like.objects.filter(post__author=request.user).count()
        post_comments_received = StoryComment.objects.filter(post__author=request.user).exclude(user=request.user).count()
        profile = Profile.objects.filter(user=request.user).first()
        profile_completion = 40
        if request.user.get_full_name():
            profile_completion += 15
        if profile and profile.image:
            profile_completion += 15
        if profile and profile.bio:
            profile_completion += 15
        if profile and profile.interests:
            profile_completion += 15
        ctx = {
            'my_posts': my_posts,
            'my_stories': my_stories,
            'my_comments': my_comments,
            'my_memberships': my_memberships,
            'saved_posts': saved_posts,
            'liked_posts_count': Like.objects.filter(user=request.user).count(),
            'saved_posts_count': SavedPost.objects.filter(user=request.user).count(),
            'post_likes_received': post_likes_received,
            'post_comments_received': post_comments_received,
            'profile_completion': min(profile_completion, 100),
            'top_posts': my_posts.annotate(
                likes_total=Count('like'),
                comments_total=Count('comment'),
            ).order_by('-likes_total', '-comments_total', '-created_at')[:3],
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        # Handle profile updates
        user = request.user
        profile, created = Profile.objects.get_or_create(user=user)
        
        if 'about' in request.POST:
            profile.about = request.POST.get('about', '')
        if 'interests' in request.POST:
            profile.interests = request.POST.get('interests', '')
        if 'bio' in request.POST:
            profile.bio = request.POST.get('bio', '')
        if 'display_name' in request.POST:
            parts = request.POST.get('display_name', '').split(' ', 1)
            user.first_name = parts[0] if parts else ''
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.save()
        if 'image' in request.FILES:
            profile.image = request.FILES['image']
        
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('accounts:profile')


class DeleteAccountView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'accounts/delete_account_confirm.html'
    success_url = reverse_lazy('home')
    
    def get_object(self, queryset=None):
        return self.request.user
        
    def delete(self, request, *args, **kwargs):
        # Delete all posts by this user first
        Post.objects.filter(author=request.user).delete()
        
        # Logout the user before deleting the account
        from django.contrib.auth import logout
        logout(request)
        
        # Delete the user account
        response = super().delete(request, *args, **kwargs)
        messages.success(request, 'Your account and all associated data have been successfully deleted.')
        return response
