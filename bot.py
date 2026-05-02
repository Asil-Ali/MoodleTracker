"""
bot.py — Telegram Chatbot يجاوب على أسئلة أسيل عن مساقاتها
يشتغل على Render Web Service كـ webhook
"""

import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ─────────────────────────────────────────────────
# إعدادات
# ─────────────────────────────────────────────────
TG_TOKEN     = os.environ.get("TG_TOKEN", "")
TG_API       = f"https://api.telegram.org/bot{TG_TOKEN}"
GROQ_KEY     = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_REPO  = os.environ.get("GH_REPO", "")  # مثال: Asil-Ali/MoodleTracker

BOT_SYSTEM = """أنت مساعد أكاديمي ذكي اسمك "مودل بوت" متخصص في مساقات أسيل الجامعية في جامعة الأقصى.

لديك بيانات كاملة عن جميع مساقاتها تشمل: الملفات، المحاضرات، الواجبات، الكويزات، الروابط، والمواعيد.

قواعد الإجابة:
- أجب بالعربية دائماً بأسلوب ودي ومباشر
- اذكر الروابط دائماً عند السؤال عنها
- إذا في موعد قريب نبّه عليه
- لا تخترع معلومات غير موجودة في البيانات
- إذا ما عندك معلومة قل ذلك بصراحة
- الإجابات مختصرة ومفيدة بدون حشو

أمثلة على ما تقدر تجيب عليه:
- "وين رابط محاضرة الأتمتة؟" ← تعطي الرابط مباشرة
- "كم واجب عندي؟" ← تعدد الواجبات ومواعيدها
- "شو في جديد اليوم؟" ← تلخص آخر تحديث
- "متى الكويز القادم؟" ← تذكر التاريخ والرابط"""


# ─────────────────────────────────────────────────
# جلب state.json من GitHub
# ─────────────────────────────────────────────────
def get_state() -> dict:
    try:
        headers = {"Accept": "application/vnd.github.v3.raw"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/state.json",
            headers=headers,
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(content)
    except Exception as e:
        print(f"[GitHub] خطأ في جلب state.json: {e}")
    return {}


# ─────────────────────────────────────────────────
# بناء ملخص البيانات للـ AI
# ─────────────────────────────────────────────────
def build_context(state: dict) -> str:
    if not state:
        return "لا توجد بيانات محفوظة حتى الآن."

    CATS = {
        "resources":    "ملفات ومحاضرات",
        "assignments":  "واجبات",
        "quizzes":      "كويزات واختبارات",
        "forums":       "منتديات",
        "wikis":        "ويكيات",
        "weekly_items": "روابط وأنشطة",
    }

    context = "بيانات مساقات أسيل الحالية:\n\n"

    for course_id, course_data in state.items():
        # نجيب اسم المساق من البيانات
        course_name = course_data.get("course_name", f"مساق {course_id}")
        course_url  = course_data.get("url", "")

        context += f"{'═'*35}\n"
        context += f"المساق: {course_name}\n"
        if course_url:
            context += f"الرابط: {course_url}\n"

        for cat, label in CATS.items():
            items = course_data.get(cat, [])
            if items:
                context += f"\n{label}:\n"
                for item in items:
                    if isinstance(item, dict):
                        context += f"  • {item.get('name', '')}"
                        if item.get('url'):
                            context += f" — {item['url']}"
                        if item.get('date'):
                            context += f" (الموعد: {item['date']})"
                        if item.get('status') and item['status'] not in ['-', '']:
                            context += f" [الحالة: {item['status']}]"
                        context += "\n"

        context += "\n"

    return context


# ─────────────────────────────────────────────────
# الرد عبر Groq
# ─────────────────────────────────────────────────
def ask_groq(question: str, context: str) -> str:
    try:
        r = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type":  "application/json",
        }, json={
            "model":       "llama-3.3-70b-versatile",
            "temperature": 0.2,
            "max_tokens":  1000,
            "messages": [
                {"role": "system", "content": f"{BOT_SYSTEM}\n\n{context}"},
                {"role": "user",   "content": question},
            ],
        }, timeout=30)

        return r.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"عذراً، حصل خطأ: {e}"


# ─────────────────────────────────────────────────
# إرسال رسالة Telegram
# ─────────────────────────────────────────────────
def send_message(chat_id: int, text: str):
    try:
        requests.post(f"{TG_API}/sendMessage", json={
            "chat_id":                  chat_id,
            "text":                     text,
            "parse_mode":               "Markdown",
            "disable_web_page_preview": True,
        }, timeout=15)
    except Exception as e:
        print(f"[Telegram] خطأ: {e}")


# ─────────────────────────────────────────────────
# Webhook endpoint
# ─────────────────────────────────────────────────
@app.route(f"/webhook/{TG_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"ok": True})

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text    = message.get("text", "").strip()

    if not chat_id or not text:
        return jsonify({"ok": True})

    print(f"[Bot] سؤال: {text}")

    # رسالة انتظار
    send_message(chat_id, "⏳ جاري البحث...")

    # جلب البيانات
    state   = get_state()
    context = build_context(state)

    # الرد عبر Groq
    answer = ask_groq(text, context)
    send_message(chat_id, answer)

    return jsonify({"ok": True})


# ─────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return "Moodle Bot يعمل ✅"


# ─────────────────────────────────────────────────
# تشغيل
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
