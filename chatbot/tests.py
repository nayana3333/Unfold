from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import ChatMessage
from .services import generate_reply, provider_status


class ChatbotTests(TestCase):
    def test_chat_api_rejects_empty_message(self):
        response = self.client.post(reverse("chatbot:chat_api"), {"text": ""})
        self.assertEqual(response.status_code, 400)

    def test_chat_api_persists_authenticated_history(self):
        user = User.objects.create_user(username="nayana", password="pass12345")
        self.client.login(username="nayana", password="pass12345")

        response = self.client.post(reverse("chatbot:chat_api"), {"text": "I feel anxious about interviews"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["emotion"], "anxious")
        self.assertEqual(ChatMessage.objects.filter(user=user).count(), 2)
        self.assertTrue(ChatMessage.objects.filter(user=user, role="assistant").exists())

    def test_chat_api_marks_distress_messages(self):
        response = self.client.post(reverse("chatbot:chat_api"), {"text": "I want to die"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ChatMessage.objects.filter(role="user", is_distress=True).exists())
        self.assertIn("immediate danger", response.json()["answer"].lower())

    def test_local_service_returns_career_guidance_without_key(self):
        result = generate_reply("Help me prepare for a job interview", history=[])

        self.assertEqual(result.provider, "local")
        self.assertIn("career", result.intents)
        self.assertIn("STAR", result.answer)

    def test_provider_status_falls_back_locally(self):
        self.assertIn(provider_status(), {"Local assistant", "OpenRouter", "OpenAI"})

    def test_local_service_answers_simple_math(self):
        result = generate_reply("2*2", history=[])

        self.assertEqual(result.provider, "local")
        self.assertEqual(result.answer, "2*2 = 4")
