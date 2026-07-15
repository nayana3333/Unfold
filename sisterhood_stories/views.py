from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q
from stories.models import Post, Story, Like, SavedPost
from community.models import Group, Discussion
from counseling.models import PsychiatristProfile
from django.contrib.auth import get_user_model

User = get_user_model()

def home(request):
    query = request.GET.get('q', '').strip()
    posts_qs = Post.objects.select_related('author').prefetch_related('like_set', 'comment_set', 'carousel_images').annotate(
        likes_total=Count('like'),
        comments_total=Count('comment'),
    ).order_by('-created_at')
    if query:
        posts_qs = posts_qs.filter(
            Q(content__icontains=query) |
            Q(author__username__icontains=query) |
            Q(pseudonym__icontains=query)
        )
    posts = list(posts_qs[:20])
    
    # Get active stories
    active_stories = []
    if request.user.is_authenticated:
        active_stories = Story.objects.filter(
            expiry__gt=timezone.now()
        ).select_related('user').order_by('-created_at')[:8]
    
    # Get liked post IDs for current user
    liked_post_ids = []
    saved_post_ids = []
    if request.user.is_authenticated and posts:
        post_ids = [p.id for p in posts]
        liked_post_ids = list(Like.objects.filter(
            user=request.user,
            post_id__in=post_ids
        ).values_list('post_id', flat=True))
        saved_post_ids = list(SavedPost.objects.filter(
            user=request.user,
            post_id__in=post_ids
        ).values_list('post_id', flat=True))
    
    return render(request, 'home.html', {
        'posts': posts,
        'active_stories': active_stories,
        'liked_post_ids': liked_post_ids,
        'saved_post_ids': saved_post_ids,
        'query': query,
        'saved_posts_count': SavedPost.objects.filter(user=request.user).count() if request.user.is_authenticated else 0,
    })


def explore(request):
    query = request.GET.get('q', '').strip()
    posts = Post.objects.select_related('author').prefetch_related('carousel_images', 'like_set', 'comment_set').annotate(
        likes_total=Count('like'),
        comments_total=Count('comment'),
    ).order_by('-likes_total', '-comments_total', '-created_at')
    people = User.objects.select_related('profile').filter(is_active=True).order_by('-date_joined')
    groups = Group.objects.filter(is_active=True).annotate(
        members_total=Count('members'),
        discussions_total=Count('discussions'),
    ).order_by('-members_total', '-discussions_total')
    counselors = PsychiatristProfile.objects.select_related('user').filter(is_verified=True).order_by('-rating', '-years_experience')
    stories = Story.objects.filter(expiry__gt=timezone.now()).select_related('user').order_by('-created_at')

    if query:
        posts = posts.filter(Q(content__icontains=query) | Q(author__username__icontains=query) | Q(pseudonym__icontains=query))
        people = people.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
        groups = groups.filter(Q(name__icontains=query) | Q(description__icontains=query))
        counselors = counselors.filter(Q(full_name__icontains=query) | Q(specialization__icontains=query) | Q(languages__icontains=query))
    elif request.user.is_authenticated:
        people = people.exclude(id=request.user.id)

    photo_posts = posts.filter(Q(image__isnull=False) | Q(carousel_images__isnull=False)).distinct()

    return render(request, 'explore.html', {
        'query': query,
        'posts': list(posts[:12]),
        'photo_posts': list(photo_posts[:9]),
        'people': list(people[:8]),
        'groups': list(groups[:6]),
        'counselors': list(counselors[:6]),
        'stories': list(stories[:8]),
        'posts_count': posts.count(),
        'people_count': people.count(),
        'groups_count': groups.count(),
        'counselors_count': counselors.count(),
    })
