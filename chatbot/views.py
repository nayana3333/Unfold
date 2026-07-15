from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from .models import ChatMessage
from .services import generate_reply, provider_status


class ChatbotView(TemplateView):
    template_name = "chatbot/chatbot.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            recent_messages = list(ChatMessage.objects.filter(user=self.request.user).order_by("-created_at")[:12])
            context["chat_history"] = list(reversed(recent_messages))
            context["history_count"] = ChatMessage.objects.filter(user=self.request.user).count()
        else:
            context["chat_history"] = []
            context["history_count"] = 0
        context["ai_provider"] = provider_status()
        return context


@require_POST
def chat_api(request):
    text = (request.POST.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "empty"}, status=400)

    history = request.session.get("chat_history", [])[-8:]
    result = generate_reply(text, history)

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": result.answer})
    request.session["chat_history"] = history[-12:]

    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key or ""
    user = request.user if request.user.is_authenticated else None
    ChatMessage.objects.bulk_create([
        ChatMessage(
            user=user,
            session_key=session_key,
            role="user",
            content=text,
            emotion=result.emotion,
            is_distress=result.distress,
        ),
        ChatMessage(
            user=user,
            session_key=session_key,
            role="assistant",
            content=result.answer,
            emotion=result.emotion,
            is_distress=result.distress,
        ),
    ])

    return JsonResponse({
        "ok": True,
        "answer": result.answer,
        "emotion": result.emotion,
        "distress": result.distress,
        "provider": result.provider,
        "intents": result.intents,
    })
