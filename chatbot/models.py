from django.db import models
from django.conf import settings


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True, related_name="chat_messages")
    session_key = models.CharField(max_length=80, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    emotion = models.CharField(max_length=30, blank=True)
    is_distress = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        owner = self.user.username if self.user_id else self.session_key or "anonymous"
        return f"{owner} {self.role}: {self.content[:40]}"
