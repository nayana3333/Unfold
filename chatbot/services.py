import json
import ast
import operator
import os
import re
from dataclasses import dataclass
from urllib import request as urlrequest


try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


DISTRESS_KEYWORDS = (
    "hopeless",
    "give up",
    "end it",
    "suicide",
    "self harm",
    "hurt myself",
    "kill myself",
    "want to die",
)

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


@dataclass
class ChatResult:
    answer: str
    provider: str
    emotion: str
    distress: bool
    intents: list


openai_client = None


def detect_emotion(text):
    t = (text or "").lower()
    distress = any(keyword in t for keyword in DISTRESS_KEYWORDS)
    if any(k in t for k in ["anxious", "panic", "anxiety", "stress", "overwhelmed", "scared", "worried", "nervous"]):
        return "anxious", distress
    if any(k in t for k in ["sad", "lonely", "down", "cry", "depressed", "low", "upset", "hurt", "disappointed"]):
        return "sad", distress
    if any(k in t for k in ["happy", "excited", "grateful", "proud", "joy", "celebrate", "great"]):
        return "happy", distress
    return "neutral", distress


def detect_intents(text):
    t = (text or "").lower()
    intents = []
    if any(k in t for k in ["career", "resume", "interview", "job", "work", "professional", "salary", "promotion"]):
        intents.append("career")
    if any(k in t for k in ["relationship", "partner", "dating", "breakup", "marriage", "friend"]):
        intents.append("relationship")
    if any(k in t for k in ["health", "period", "pregnancy", "medical", "doctor", "symptom"]):
        intents.append("health")
    if any(k in t for k in ["mentor", "guidance", "advice", "help", "support"]):
        intents.append("support")
    if any(k in t for k in ["report", "abuse", "harassment", "unsafe", "danger"]):
        intents.append("report")
    if any(k in t for k in ["self care", "wellness", "meditation", "exercise", "fitness"]):
        intents.append("wellness")
    return intents


def system_prompt():
    return (
        "You are Unfold AI, a warm, careful support assistant for women. "
        "Respond with empathy, clarity, and practical next steps. "
        "Offer gentle guidance such as grounding, journaling, boundaries, career planning, and self-care. "
        "Maintain short-term context from recent conversation turns. "
        "If self-harm, violence, abuse, or immediate danger appears, encourage urgent local help and professional support. "
        "Do not pretend to be a therapist, doctor, lawyer, or emergency service. "
        "Do not diagnose, prescribe medication, or make legal claims. "
        "Keep responses under 180 words, conversational, and structured with 2-4 short bullets when useful. "
        "Do not use emojis."
    )


def provider_status():
    if os.getenv("OPENROUTER_API_KEY"):
        return "OpenRouter"
    if os.getenv("OPENAI_API_KEY"):
        return "OpenAI"
    return "Local assistant"


def _safe_eval_math(node):
    if isinstance(node, ast.Expression):
        return _safe_eval_math(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPERATORS:
        left = _safe_eval_math(node.left)
        right = _safe_eval_math(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("Exponent too large")
        return SAFE_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPERATORS:
        return SAFE_OPERATORS[type(node.op)](_safe_eval_math(node.operand))
    raise ValueError("Unsupported expression")


def simple_math_answer(text):
    expression = (text or "").strip()
    if not re.fullmatch(r"[\d\s\.\+\-\*\/\%\(\)]+", expression):
        return None
    try:
        result = _safe_eval_math(ast.parse(expression, mode="eval"))
    except Exception:
        return None
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{expression} = {result}"


def call_openrouter(messages):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    payload = {
        "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        "messages": messages,
        "temperature": float(os.getenv("CHATBOT_TEMPERATURE", "0.65")),
        "max_tokens": int(os.getenv("CHATBOT_MAX_TOKENS", "340")),
    }
    req = urlrequest.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://127.0.0.1:8001"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "Unfold"),
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=int(os.getenv("CHATBOT_TIMEOUT_SECONDS", "25"))) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def call_openai(messages):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not OPENAI_AVAILABLE:
        return None

    global openai_client
    if openai_client is None:
        openai_client = OpenAI(api_key=api_key)
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        messages=messages,
        max_tokens=int(os.getenv("CHATBOT_MAX_TOKENS", "340")),
        temperature=float(os.getenv("CHATBOT_TEMPERATURE", "0.65")),
    )
    return response.choices[0].message.content.strip()


def local_answer(text, emotion, distress, intents):
    math_response = simple_math_answer(text)
    if math_response:
        return math_response

    if distress:
        return (
            "I am really concerned about what you shared. You do not have to handle this alone.\n\n"
            "- If you are in immediate danger, contact local emergency help now.\n"
            "- Move near a trusted person if possible.\n"
            "- Use Unfold counseling or a qualified professional for support.\n\n"
            "Can you tell me whether you are safe right now?"
        )
    if emotion == "anxious":
        return (
            "I hear that anxiety. Let us make the next minute smaller.\n\n"
            "- Breathe in for 4, hold for 2, exhale for 6.\n"
            "- Name 5 things you can see and 3 things you can touch.\n"
            "- Write one sentence: 'Right now, I need...'\n\n"
            "What triggered the anxiety today?"
        )
    if emotion == "sad":
        return (
            "I am sorry it feels heavy. Your feelings are valid.\n\n"
            "- Do one gentle thing: water, food, shower, or fresh air.\n"
            "- Message one safe person if you can.\n"
            "- If this has been lasting, counseling support may help.\n\n"
            "Do you want comfort, advice, or a plan?"
        )
    if "career" in intents:
        return (
            "Let us work on your career clearly.\n\n"
            "- For resume: quantify impact, tools, and outcomes.\n"
            "- For interviews: prepare 5 STAR stories.\n"
            "- For confidence: practice a 45-second project pitch.\n\n"
            "Tell me the role and your strongest project."
        )
    if "report" in intents:
        return (
            "Your safety matters first.\n\n"
            "- If there is immediate danger, contact emergency help.\n"
            "- Save screenshots or details if it is safe.\n"
            "- Use the platform report option or talk to a counselor.\n\n"
            "Do you want help writing a clear report?"
        )
    if "health" in intents:
        return (
            "I can support general wellness, but medical symptoms need a qualified professional.\n\n"
            "- Track symptoms, timing, and severity.\n"
            "- Seek urgent care for severe pain, bleeding, fainting, or danger signs.\n"
            "- For everyday wellness, we can make a simple routine.\n\n"
            "What are you noticing?"
        )
    return (
        "I am here with you. Tell me what is happening, and we can slow it down together.\n\n"
        "- If you want comfort, I will listen.\n"
        "- If you want action, I can help make a plan.\n"
        "- If it is safety-related, we can focus on next safe steps."
    )


def build_messages(text, history):
    messages = [{"role": "system", "content": system_prompt()}]
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": text})
    return messages


def safety_wrap(answer, distress):
    if distress and "immediate danger" not in answer.lower():
        return (
            f"{answer}\n\n"
            "If you are in immediate danger, please contact local emergency help now. "
            "Unfold can support you, but it is not an emergency service."
        )
    return answer


def generate_reply(text, history=None):
    history = history or []
    emotion, distress = detect_emotion(text)
    intents = detect_intents(text)
    messages = build_messages(text, history)

    provider = "local"
    answer = None
    for candidate_provider, caller in (("openrouter", call_openrouter), ("openai", call_openai)):
        try:
            answer = caller(messages)
            if answer:
                provider = candidate_provider
                break
        except Exception:
            answer = None

    if not answer:
        answer = local_answer(text, emotion, distress, intents)

    return ChatResult(
        answer=safety_wrap(answer, distress),
        provider=provider,
        emotion=emotion,
        distress=distress,
        intents=intents,
    )
