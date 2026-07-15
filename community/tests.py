from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Comment, Discussion, DiscussionLike, Group, GroupMember


class CommunityFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass12345")
        self.member = User.objects.create_user(username="member", password="pass12345")
        self.outsider = User.objects.create_user(username="outsider", password="pass12345")
        self.group = Group.objects.create(
            name="Career Circle",
            description="A safe space for career questions.",
            creator=self.owner,
            visibility="public",
        )
        GroupMember.objects.create(group=self.group, user=self.owner, role="admin")
        GroupMember.objects.create(group=self.group, user=self.member, role="member")
        self.discussion = Discussion.objects.create(
            group=self.group,
            author=self.member,
            title="Interview prep",
            content="How do I explain project impact?",
        )

    def test_authenticated_user_can_join_public_group(self):
        self.client.login(username="outsider", password="pass12345")
        response = self.client.post(reverse("community:join_group", args=[self.group.id]))

        self.assertRedirects(response, reverse("community:group_detail", args=[self.group.id]))
        self.assertTrue(GroupMember.objects.filter(group=self.group, user=self.outsider).exists())

    def test_private_group_blocks_direct_join(self):
        private_group = Group.objects.create(
            name="Private",
            description="Invite only",
            creator=self.owner,
            visibility="private",
        )
        self.client.login(username="outsider", password="pass12345")
        response = self.client.post(reverse("community:join_group", args=[private_group.id]))

        self.assertRedirects(response, reverse("community:list"))
        self.assertFalse(GroupMember.objects.filter(group=private_group, user=self.outsider).exists())

    def test_non_member_cannot_create_discussion(self):
        self.client.login(username="outsider", password="pass12345")
        response = self.client.post(
            reverse("community:create_discussion", args=[self.group.id]),
            {"title": "Hello", "content": "Can I post?"},
        )

        self.assertRedirects(response, reverse("community:group_detail", args=[self.group.id]))
        self.assertFalse(Discussion.objects.filter(author=self.outsider).exists())

    def test_member_can_like_discussion(self):
        self.client.login(username="member", password="pass12345")
        response = self.client.post(reverse("community:toggle_like", args=[self.discussion.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(DiscussionLike.objects.filter(discussion=self.discussion, user=self.member).exists())

    def test_owner_can_pin_and_close_discussion(self):
        self.client.login(username="owner", password="pass12345")
        self.client.post(reverse("community:update_discussion", args=[self.discussion.id, "pin"]))
        self.client.post(reverse("community:update_discussion", args=[self.discussion.id, "close"]))

        self.discussion.refresh_from_db()
        self.assertTrue(self.discussion.is_pinned)
        self.assertTrue(self.discussion.is_closed)

    def test_closed_discussion_blocks_new_comments(self):
        self.discussion.is_closed = True
        self.discussion.save(update_fields=["is_closed"])
        self.client.login(username="member", password="pass12345")
        response = self.client.post(
            reverse("community:create_comment", args=[self.discussion.id]),
            {"content": "Adding one more thought."},
        )

        self.assertRedirects(response, reverse("community:discussion_detail", args=[self.discussion.id]))
        self.assertFalse(Comment.objects.filter(content__icontains="one more").exists())
