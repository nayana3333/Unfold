from django.views.generic import ListView, CreateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from .models import Group, GroupMember, Discussion, DiscussionLike, Comment
from .forms import GroupForm, DiscussionForm, CommentForm


class CommunityListView(ListView):
    template_name = "community/community_list.html"
    context_object_name = "groups"
    
    def get_queryset(self):
        # Get all public groups or groups user is member of
        if self.request.user.is_authenticated:
            user_groups = GroupMember.objects.filter(user=self.request.user).values_list('group_id', flat=True)
            queryset = Group.objects.filter(
                Q(visibility='public') | Q(id__in=user_groups),
                is_active=True
            ).annotate(
                member_count=Count('members')
            ).select_related('creator').prefetch_related('members__user')
        else:
            queryset = Group.objects.filter(visibility='public', is_active=True).annotate(
                member_count=Count('members')
            ).select_related('creator')
        
        # Add membership status for each group
        if self.request.user.is_authenticated:
            user_group_ids = set(GroupMember.objects.filter(user=self.request.user).values_list('group_id', flat=True))
            for group in queryset:
                group.user_is_member = group.id in user_group_ids
        else:
            for group in queryset:
                group.user_is_member = False
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # My groups
        if self.request.user.is_authenticated:
            my_group_ids = GroupMember.objects.filter(user=self.request.user).values_list('group_id', flat=True)
            context['my_groups'] = Group.objects.filter(id__in=my_group_ids, is_active=True).annotate(
                member_count=Count('members')
            )
            
            # Suggested groups (groups user is not a member of)
            context['suggested_groups'] = Group.objects.filter(
                visibility='public',
                is_active=True
            ).exclude(id__in=my_group_ids).annotate(
                member_count=Count('members')
            )[:5]
        else:
            context['my_groups'] = Group.objects.none()
            context['suggested_groups'] = Group.objects.filter(
                visibility='public',
                is_active=True
            ).annotate(member_count=Count('members'))[:5]
        
        # Recent discussions across all groups
        context['recent_discussions'] = Discussion.objects.select_related(
            'group', 'author'
        ).prefetch_related('likes', 'comments').order_by('-created_at')[:10]
        context['group_count'] = context['groups'].count()
        context['discussion_count'] = Discussion.objects.filter(group__in=context['groups']).count()
        context['member_count'] = GroupMember.objects.filter(group__in=context['groups']).count()
        
        return context


class CreateGroupView(LoginRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = "community/create_group.html"
    
    def form_valid(self, form):
        group = form.save(commit=False)
        group.creator = self.request.user
        group.save()
        
        # Add creator as admin member
        GroupMember.objects.create(
            group=group,
            user=self.request.user,
            role='admin'
        )
        
        messages.success(self.request, f'Group "{group.name}" created successfully!')
        return redirect('community:group_detail', pk=group.pk)


class GroupDetailView(DetailView):
    model = Group
    template_name = "community/group_detail.html"
    context_object_name = "group"

    def get_object(self, queryset=None):
        group = super().get_object(queryset)
        user = self.request.user
        if group.visibility == 'private' and not group.is_member(user) and not (user.is_authenticated and user.is_staff):
            raise Http404("Group not found")
        return group

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.get_object()
        
        # Check if user is member
        context['is_member'] = False
        context['is_creator'] = False
        if self.request.user.is_authenticated:
            context['is_member'] = group.is_member(self.request.user)
            context['is_creator'] = group.is_creator(self.request.user)
        
        # Get discussions with like status
        discussions = group.discussions.select_related(
            'author'
        ).prefetch_related('likes', 'comments').order_by('-is_pinned', '-created_at')
        
        # Add liked status for each discussion if user is authenticated
        if self.request.user.is_authenticated:
            for discussion in discussions:
                discussion.user_liked = discussion.is_liked_by(self.request.user)
                discussion.user_can_manage = discussion.can_manage(self.request.user)
        
        context['discussions'] = discussions
        context['discussion_count'] = discussions.count()
        context['comment_count'] = Comment.objects.filter(discussion__group=group).count()
        
        # Get members
        context['members'] = group.members.select_related('user')[:10]
        context['member_count'] = group.member_count()
        
        # Discussion form
        if self.request.user.is_authenticated and context['is_member']:
            context['discussion_form'] = DiscussionForm()
        
        return context


class JoinGroupView(LoginRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk, is_active=True)
        
        if group.is_member(request.user):
            messages.info(request, f'You are already a member of "{group.name}"')
            return redirect('community:group_detail', pk=group.pk)
        
        if group.visibility == 'private':
            messages.error(request, 'This is a private group. You need an invitation to join.')
            return redirect('community:list')
        
        GroupMember.objects.create(
            group=group,
            user=request.user,
            role='member'
        )
        
        messages.success(request, f'You have joined "{group.name}"!')
        return redirect('community:group_detail', pk=group.pk)


class LeaveGroupView(LoginRequiredMixin, View):
    def post(self, request, pk):
        group = get_object_or_404(Group, pk=pk)
        
        if not group.is_member(request.user):
            messages.error(request, 'You are not a member of this group.')
            return redirect('community:group_detail', pk=group.pk)
        
        if group.is_creator(request.user):
            messages.error(request, 'Group creators cannot leave their groups.')
            return redirect('community:group_detail', pk=group.pk)
        
        GroupMember.objects.filter(group=group, user=request.user).delete()
        messages.success(request, f'You have left "{group.name}"')
        return redirect('community:list')


class CreateDiscussionView(LoginRequiredMixin, CreateView):
    model = Discussion
    form_class = DiscussionForm
    
    def form_valid(self, form):
        group = get_object_or_404(Group, pk=self.kwargs['group_id'], is_active=True)
        
        # Check if user is member
        if not group.is_member(self.request.user):
            messages.error(self.request, 'You must be a member to create discussions.')
            return redirect('community:group_detail', pk=group.pk)
        
        discussion = form.save(commit=False)
        discussion.group = group
        discussion.author = self.request.user
        discussion.save()
        
        messages.success(self.request, 'Discussion created successfully!')
        return redirect('community:group_detail', pk=group.pk)


class DiscussionDetailView(DetailView):
    model = Discussion
    template_name = "community/discussion_detail.html"
    context_object_name = "discussion"

    def get_object(self, queryset=None):
        discussion = super().get_object(queryset)
        user = self.request.user
        group = discussion.group
        if group.visibility == 'private' and not group.is_member(user) and not (user.is_authenticated and user.is_staff):
            raise Http404("Discussion not found")
        return discussion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        discussion = self.get_object()
        
        context['is_member'] = False
        if self.request.user.is_authenticated:
            context['is_member'] = discussion.group.is_member(self.request.user)
            context['is_liked'] = discussion.is_liked_by(self.request.user)
            context['can_manage'] = discussion.can_manage(self.request.user)
        else:
            context['can_manage'] = False
        
        # Get comments
        context['comments'] = discussion.comments.select_related('author').order_by('created_at')
        
        # Comment form
        if context['is_member'] and not discussion.is_closed:
            context['comment_form'] = CommentForm()
        
        return context


class ToggleDiscussionLikeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        discussion = get_object_or_404(Discussion, pk=pk)
        
        if not discussion.group.is_member(request.user):
            return JsonResponse({'error': 'You must be a member to like discussions.'}, status=403)
        
        like, created = DiscussionLike.objects.get_or_create(
            discussion=discussion,
            user=request.user
        )
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        
        # Refresh discussion to get updated like count
        discussion.refresh_from_db()
        
        return JsonResponse({
            'liked': liked,
            'like_count': discussion.like_count()
        })


class CreateCommentView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    
    def form_valid(self, form):
        discussion = get_object_or_404(Discussion, pk=self.kwargs['discussion_id'])
        
        if not discussion.group.is_member(self.request.user):
            messages.error(self.request, 'You must be a member to comment.')
            return redirect('community:discussion_detail', pk=discussion.pk)
        if discussion.is_closed:
            messages.error(self.request, 'This discussion is closed for new comments.')
            return redirect('community:discussion_detail', pk=discussion.pk)
        
        comment = form.save(commit=False)
        comment.discussion = discussion
        comment.author = self.request.user
        comment.save()
        
        messages.success(self.request, 'Comment added!')
        return redirect('community:discussion_detail', pk=discussion.pk)


class UpdateDiscussionView(LoginRequiredMixin, View):
    allowed_actions = {"pin", "unpin", "close", "reopen"}

    def post(self, request, pk, action):
        discussion = get_object_or_404(Discussion.objects.select_related("group", "author"), pk=pk)
        if action not in self.allowed_actions:
            raise Http404("Unknown discussion action.")
        if not discussion.can_manage(request.user):
            raise Http404("You cannot manage this discussion.")

        if action == "pin":
            discussion.is_pinned = True
            message = "Discussion pinned."
        elif action == "unpin":
            discussion.is_pinned = False
            message = "Discussion unpinned."
        elif action == "close":
            discussion.is_closed = True
            message = "Discussion closed."
        else:
            discussion.is_closed = False
            message = "Discussion reopened."

        discussion.save(update_fields=["is_pinned", "is_closed", "updated_at"])
        messages.success(request, message)
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("community:discussion_detail", pk=discussion.pk)
