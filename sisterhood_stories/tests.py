from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from community.models import Group
from counseling.models import PsychiatristProfile
from stories.models import Post


class ExplorePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="nayana", password="StrongPass123!")
        Post.objects.create(author=self.user, content="Career confidence post")
        Group.objects.create(
            name="Career Circle",
            description="Career support and peer guidance",
            creator=self.user,
        )
        counselor_user = User.objects.create_user(username="doctor", password="StrongPass123!")
        PsychiatristProfile.objects.create(
            user=counselor_user,
            full_name="Dr. Ananya Rao",
            license_no="LIC-200",
            specialization="Anxiety",
            years_experience=5,
            is_verified=True,
            is_female=True,
        )

    def test_explore_page_renders_core_sections(self):
        response = self.client.get(reverse("explore"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find posts, stories, people, and care.")
        self.assertContains(response, "Photo wall")
        self.assertContains(response, "Trending posts")
        self.assertContains(response, "Active groups")
        self.assertContains(response, "Verified care")

    def test_explore_search_filters_posts(self):
        response = self.client.get(reverse("explore"), {"q": "Career"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Career confidence post")
        self.assertContains(response, "Career Circle")
