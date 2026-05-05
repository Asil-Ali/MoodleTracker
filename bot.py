"""
bot.py — Telegram Chatbot ذكي بـ Two-Step Groq Routing
الخطوة 1: Groq يحدد المساق (~100 توكن)
الخطوة 2: Groq يجاوب بالبيانات الصح فقط (~800 توكن)
إجمالي: ~900 توكن بدل 6000
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
GITHUB_REPO  = os.environ.get("GH_REPO", "")

# حالة المحادثة — يتذكر اختيار المساق
user_sessions = {}

BOT_SYSTEM = """أنت مساعد أكاديمي ذكي اسمك "مودل بوت" لطالبة في جامعة الأقصى اسمها أسيل.

قواعد الإجابة:
- أجب بالعربية دائماً بأسلوب ودي ومباشر
- اذكر الروابط دائماً عند السؤال عنها
- إذا في موعد قريب نبّه عليه بوضوح
- لا تخترع معلومات غير موجودة في البيانات
- الإجابة مختصرة ومفيدة بدون حشو
- لو ما لقيت المعلومة قل ذلك بصراحة"""

ROUTER_PROMPT = """أنت نظام تصنيف أسئلة. مهمتك تحديد أي مساق يقصده المستخدم.

قائمة المساقات المتاحة (بالمعرف والاسم):
{courses_list}

السؤال: {question}

أجب بـ JSON فقط بهذا الشكل بدون أي كلام إضافي:
{{"course_id": "المعرف أو null إذا السؤال عام", "confidence": "high/low"}}

- إذا السؤال يخص مساقاً محدداً: أعط معرفه
- إذا السؤال عام (مثل: شو عندي اليوم، كم واجب عندي): أعط null
- إذا غير واضح: أعط null"""


# ─────────────────────────────────────────────────
# جلب state.json من GitHub
# ─────────────────────────────────────────────────
def get_state() -> dict:
    try:
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/state.json",
            headers=headers,
            timeout=15
        )
        if r.status_code == 200:
            import base64
            data    = r.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(content)
        else:
            print(f"[GitHub] status: {r.status_code}")
    except Exception as e:
        print(f"[GitHub] خطأ: {e}")
    return {}


# ─────────────────────────────────────────────────
# الخطوة 1: تحديد المساق بـ Groq (~100 توكن)
# ─────────────────────────────────────────────────
def route_question(question: str, state: dict) -> str | None:
    """يرجع course_id أو None لو السؤال عام"""
    if not state:
        return None

    # بناء قائمة مختصرة للمساقات
    courses_list = ""
    for cid, cdata in state.items():
        name = cdata.get("course_name", f"مساق {cid}")
        courses_list += f"- معرف: {cid} | اسم: {name}\n"

    prompt = ROUTER_PROMPT.format(
        courses_list=courses_list,
        question=question
    )

    try:
        r = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type":  "application/json",
        }, json={
            "model":       "llama-3.1-8b-instant",
            "temperature": 0,
            "max_tokens":  50,
            "messages": [{"role": "user", "content": prompt}],
        }, timeout=15)

        result = r.json()
        if "choices" not in result:
            return None

        text = result["choices"][0]["message"]["content"].strip()
        # نظّف الـ JSON
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        cid = data.get("course_id")
        if cid and cid != "null" and cid in state:
            return cid
        return None

    except Exception as e:
        print(f"[Router] خطأ: {e}")
        return None


# ─────────────────────────────────────────────────
# بناء context مساق واحد (~400 توكن)
# ─────────────────────────────────────────────────
def build_course_context(cid: str, cdata: dict) -> str:
    CATS = {
        "resources":    "ملفات ومحاضرات",
        "assignments":  "واجبات",
        "quizzes":      "كويزات واختبارات",
        "forums":       "منتديات",
        "wikis":        "ويكيات",
        "weekly_items": "روابط وأنشطة",
    }

    ctx  = f"المساق: {cdata.get('course_name', '')}\n"
    ctx += f"الرابط: {cdata.get('url', '')}\n\n"

    for cat, label in CATS.items():
        items = cdata.get(cat, [])
        if not items:
            continue
        ctx += f"{label}:\n"
        for item in items:
            if isinstance(item, dict):
                ctx += f"  • {item.get('name', '')}"
                if item.get("url"):
                    ctx += f" — {item['url']}"
                if item.get("date"):
                    ctx += f" (الموعد: {item['date']})"
                if item.get("status") and item["status"] not in ["-", ""]:
                    ctx += f" [الحالة: {item['status']}]"
                ctx += "\n"

    return ctx


# ─────────────────────────────────────────────────
# بناء context ملخص لكل المساقات (~600 توكن)
# ─────────────────────────────────────────────────
def build_summary_context(state: dict) -> str:
    ctx = "ملخص جميع مساقاتي:\n\n"

    for cid, cdata in state.items():
        name = cdata.get("course_name", "")
        url  = cdata.get("url", "")

        assignments = cdata.get("assignments", [])
        quizzes     = cdata.get("quizzes", [])
        resources   = cdata.get("resources", [])

        ctx += f"━ {name}\n"
        ctx += f"  الرابط: {url}\n"

        # الواجبات مع مواعيدها
        if assignments:
            ctx += "  الواجبات:\n"
            for a in assignments:
                if isinstance(a, dict):
                    ctx += f"    • {a.get('name', '')} — {a.get('url', '')}"
                    if a.get("date"):
                        ctx += f" (الموعد: {a['date']})"
                    ctx += "\n"

        # الكويزات مع مواعيدها
        if quizzes:
            ctx += "  الكويزات:\n"
            for q in quizzes:
                if isinstance(q, dict):
                    ctx += f"    • {q.get('name', '')} — {q.get('url', '')}"
                    if q.get("date"):
                        ctx += f" (الموعد: {q['date']})"
                    ctx += "\n"

        # عدد الملفات فقط
        if resources:
            ctx += f"  الملفات: {len(resources)} ملف/رابط\n"

        ctx += "\n"

    return ctx


# ─────────────────────────────────────────────────
# الخطوة 2: الجواب الكامل بـ Groq (~800 توكن)
# ─────────────────────────────────────────────────
def ask_groq(question: str, context: str) -> str:
    try:
        r = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type":  "application/json",
        }, json={
            "model":       "llama-3.1-8b-instant",
            "temperature": 0.2,
            "max_tokens":  800,
            "messages": [
                {"role": "system", "content": f"{BOT_SYSTEM}\n\nبيانات المساقات:\n{context}"},
                {"role": "user",   "content": question},
            ],
        }, timeout=30)

        result = r.json()

        if "error" in result:
            print(f"[Groq] خطأ: {result['error']}")
            return "عذراً، حصل خطأ مؤقت. حاولي مرة ثانية بعد ثوانٍ."

        if "choices" not in result:
            print(f"[Groq] رد غير متوقع: {result}")
            return "عذراً، لم أتمكن من معالجة سؤالك. حاولي مرة ثانية."

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        print(f"[Groq] استثناء: {e}")
        return "عذراً، حصل خطأ تقني. حاولي مرة ثانية."


# ─────────────────────────────────────────────────
# إرسال رسالة Telegram
# ─────────────────────────────────────────────────
def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {
        "chat_id":                  chat_id,
        "text":                     text,
        "parse_mode":               "Markdown",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"{TG_API}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        print(f"[Telegram] خطأ: {e}")


# ─────────────────────────────────────────────────
# إرسال أزرار اختيار المساق
# ─────────────────────────────────────────────────
def send_course_selector(chat_id: int, state: dict, question: str):
    """يعرض أزرار المساقات لما السؤال غامض"""
    user_sessions[chat_id] = {"pending_question": question}

    buttons = []
    for cid, cdata in state.items():
        name = cdata.get("course_name", f"مساق {cid}")
        # نختصر الاسم لو طويل
        short_name = name[:30] + "..." if len(name) > 30 else name
        buttons.append([{"text": short_name, "callback_data": f"course:{cid}"}])

    buttons.append([{"text": "📚 جميع المساقات", "callback_data": "course:all"}])

    send_message(chat_id,
        "لم أتأكد من المساق المقصود — اختاري من القائمة:",
        reply_markup={"inline_keyboard": buttons}
    )


# ─────────────────────────────────────────────────
# معالجة Callback (ضغطة زر)
# ─────────────────────────────────────────────────
def handle_callback(callback: dict, state: dict):
    chat_id  = callback["message"]["chat"]["id"]
    data     = callback.get("data", "")
    callback_id = callback.get("id", "")

    # أكّد استلام الضغطة
    try:
        requests.post(f"{TG_API}/answerCallbackQuery",
                      json={"callback_query_id": callback_id}, timeout=10)
    except:
        pass

    session  = user_sessions.get(chat_id, {})
    question = session.get("pending_question", "")

    if not question:
        send_message(chat_id, "اكتبي سؤالك من جديد 👇")
        return

    send_message(chat_id, "⏳ جاري البحث...")

    if data == "course:all":
        context = build_summary_context(state)
    elif data.startswith("course:"):
        cid = data.replace("course:", "")
        if cid in state:
            context = build_course_context(cid, state[cid])
        else:
            context = build_summary_context(state)
    else:
        context = build_summary_context(state)

    answer = ask_groq(question, context)
    send_message(chat_id, answer)

    # امسح الجلسة
    user_sessions.pop(chat_id, None)


# ─────────────────────────────────────────────────
# Webhook endpoint
# ─────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data:
        return jsonify({"ok": True})

    state = get_state()

    # ── معالجة ضغطة زر ──────────────────────────
    if "callback_query" in data:
        handle_callback(data["callback_query"], state)
        return jsonify({"ok": True})

    # ── معالجة رسالة نصية ───────────────────────
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text    = message.get("text", "").strip()

    if not chat_id or not text:
        return jsonify({"ok": True})

    print(f"[Bot] سؤال: {text}")

    if not state:
        send_message(chat_id, "⚠️ لا توجد بيانات محفوظة بعد. شغّلي الـ tracker أولاً.")
        return jsonify({"ok": True})

    send_message(chat_id, "⏳ جاري البحث...")

    # ── الخطوة 1: تحديد المساق ──────────────────
    course_id = route_question(text, state)

    if course_id:
        # سؤال محدد → بيانات مساق واحد فقط
        print(f"[Router] مساق محدد: {course_id}")
        context = build_course_context(course_id, state[course_id])
        answer  = ask_groq(text, context)
        send_message(chat_id, answer)
    else:
        # سؤال عام → نحاول بالملخص
        print("[Router] سؤال عام")
        context = build_summary_context(state)
        answer  = ask_groq(text, context)

        # لو الجواب ما كان كافياً نعرض الأزرار
        if "لا أعرف" in answer or "لا توجد" in answer or "غير واضح" in answer:
            send_message(chat_id, answer)
            send_course_selector(chat_id, state, text)
        else:
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
