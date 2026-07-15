from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Post, Story


class AnonymousPublishingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="nayana", password="StrongPass123!")

    def test_anonymous_post_keeps_pseudonym(self):
        self.client.login(username="nayana", password="StrongPass123!")

        response = self.client.post(
            reverse("stories:post_create"),
            {
                "content": "Sharing this privately.",
                "is_anonymous": "on",
                "pseudonym": "Quiet Voice",
                "allow_comments": "on",
            },
        )

        self.assertRedirects(response, reverse("home"))
        post = Post.objects.get(author=self.user)
        self.assertTrue(post.is_anonymous)
        self.assertEqual(post.pseudonym, "Quiet Voice")

    def test_visible_post_clears_pseudonym(self):
        self.client.login(username="nayana", password="StrongPass123!")

        self.client.post(
            reverse("stories:post_create"),
            {
                "content": "Sharing with my name.",
                "pseudonym": "Should disappear",
                "allow_comments": "on",
            },
        )

        post = Post.objects.get(author=self.user)
        self.assertFalse(post.is_anonymous)
        self.assertEqual(post.pseudonym, "")

    def test_anonymous_story_display_helpers_hide_user(self):
        self.client.login(username="nayana", password="StrongPass123!")

        response = self.client.post(
            reverse("stories:story_create"),
            {
                "content": "A private story.",
                "is_anonymous": "on",
                "pseudonym": "Bloom",
            },
        )

        self.assertRedirects(response, reverse("home"))
        story = Story.objects.get(user=self.user)
        self.assertTrue(story.is_anonymous)
        self.assertEqual(story.display_name(), "Bloom")
        self.assertEqual(story.display_initial(), "B")

    def test_visible_story_clears_pseudonym(self):
        self.client.login(username="nayana", password="StrongPass123!")

        self.client.post(
            reverse("stories:story_create"),
            {
                "content": "A visible story.",
                "pseudonym": "Should disappear",
            },
        )

        story = Story.objects.get(user=self.user)
        self.assertFalse(story.is_anonymous)
        self.assertEqual(story.pseudonym, "")
