from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
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

    def test_post_detail_shows_report_link(self):
        post = Post.objects.create(author=self.user, content="Reportable content")
        other = User.objects.create_user(username="viewer", password="StrongPass123!")
        self.client.login(username="viewer", password="StrongPass123!")

        response = self.client.get(reverse("stories:post_detail", args=[post.id]))

        self.assertContains(
            response,
            reverse("moderation:create_report", args=["stories", "post", post.id]),
        )

    def test_post_rejects_disallowed_file_extension(self):
        self.client.login(username="nayana", password="StrongPass123!")
        malicious = SimpleUploadedFile("payload.exe", b"MZ fake binary", content_type="application/octet-stream")

        response = self.client.post(
            reverse("stories:post_create"),
            {"content": "Sharing an attachment.", "allow_comments": "on", "file": malicious},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(content="Sharing an attachment.").exists())

    def test_post_accepts_allowed_file_extension(self):
        self.client.login(username="nayana", password="StrongPass123!")
        attachment = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")

        response = self.client.post(
            reverse("stories:post_create"),
            {"content": "Sharing a text file.", "allow_comments": "on", "file": attachment},
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(Post.objects.filter(content="Sharing a text file.").exists())
