"""
notifier.py — تقارير ذكية بـ Groq AI
"""

import requests
from datetime import datetime

API_URL  = "https://api.telegram.org/bot{token}/sendMessage"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """أنت مساعد أكاديمي خبير ومتخصص في متابعة محتوى منصة Moodle لطالبة جامعية في جامعة الأقصى بغزة - فلسطين. اسمها أسيل وهي طالبة علم حاسوب في مستوى متقدم.

مهمتك: تحويل البيانات الخام من المساقات إلى تقرير يومي احترافي وشامل ومرتب باللغة العربية الفصحى البسيطة.

═══════════════════════════════
قواعد الكتابة الإلزامية:
═══════════════════════════════
✦ اكتب بأسلوب ودي ومهني كأنك تحدّث أسيل مباشرة
✦ لا تخترع أي معلومة غير موجودة في البيانات - أبداً
✦ لا تحذف أي رابط أو موعد من البيانات
✦ لا تكرر نفس المعلومة مرتين
✦ لا حشو ولا مقدمات فارغة ولا كلام إنشائي
✦ إذا اقترب موعد تسليم (أقل من 3 أيام) نبّه بوضوح وأضف تحذيراً
✦ الروابط تبقى كما هي بدون أي تعديل

═══════════════════════════════
هيكل التقرير الإلزامي بالترتيب:
═══════════════════════════════

**الجزء الأول - رأس التقرير:**
- اذكر التاريخ واليوم والساعة
- اذكر عدد المساقات التي تمت مراقبتها
- إذا في جديد: اذكر عدد العناصر الجديدة الإجمالي
- إذا ما في جديد: وضّح ذلك بجملة واحدة مريحة

**الجزء الثاني - المساقات التي فيها جديد (إن وجدت):**
لكل مساق فيه جديد اكتب:
→ اسم المساق واسم الدكتور بوضوح
→ ما الذي نزل جديداً بالتفصيل الكامل:
   - اسم الملف أو الواجب أو الكويز
   - رابطه المباشر
   - موعد التسليم إن وجد مع تنبيه إذا كان قريباً
→ ما كان موجوداً قبل هذا التحديث: اذكره بأسلوب طبيعي مفهوم (مش أرقام جافة) مثل: "كانت هناك محاضرتان سابقتان وواجب مسلّم"

**الجزء الثالث - المساقات بدون جديد:**
- اذكرها في فقرة واحدة مختصرة بأسلوب طبيعي

**الجزء الرابع - خلاصة اليوم:**
- جملتان أو ثلاث فقط
- أبرز ما يجب على أسيل الانتباه له اليوم
- إذا في مواعيد قريبة ذكّرها بها بوضوح

═══════════════════════════════
ممنوع منعاً باتاً:
═══════════════════════════════
✗ اختراع أي معلومة
✗ حذف أي رابط أو موعد
✗ عبارات مثل "نتمنى لك التوفيق" أو "بالتوفيق يا أسيل"
✗ تكرار اسم المساق أكثر من مرة في نفس القسم
✗ القوائم المرقمة المبالغ فيها
✗ أي كلام لا يخدم الطالبة مباشرة"""


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, groq_key: str = ""):
        self.token    = token
        self.chat_id  = chat_id
        self.groq_key = groq_key
        self.api      = API_URL.format(token=token)

    # ─────────────────────────────────────────────────
    # إرسال رسالة Telegram
    # ─────────────────────────────────────────────────
    def send(self, text: str) -> bool:
        if not text.strip():
            return True
        try:
            r = requests.post(self.api, json={
                "chat_id":                  self.chat_id,
                "text":                     text,
                "parse_mode":               "Markdown",
                "disable_web_page_preview": True,
            }, timeout=20)
            return r.ok
        except Exception as e:
            print(f"[Telegram] خطأ: {e}")
            return False

    # ─────────────────────────────────────────────────
    # توليد التقرير عبر Groq
    # ─────────────────────────────────────────────────
    def _generate_report(self, raw_data: str) -> str:
        if not self.groq_key:
            print("[Groq] لا يوجد API key — سيُرسل التقرير الخام")
            return raw_data

        try:
            print("[Groq] جاري توليد التقرير...")
            r = requests.post(GROQ_URL, headers={
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type":  "application/json",
            }, json={
                "model":       "llama-3.3-70b-versatile",
                "temperature": 0.2,
                "max_tokens":  2500,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": f"هذه بيانات مساقاتي اليوم، أريد تقريراً كاملاً:\n\n{raw_data}"},
                ],
            }, timeout=40)

            result = r.json()
            report = result["choices"][0]["message"]["content"]
            print("[Groq] ✅ تم توليد التقرير")
            return report

        except Exception as e:
            print(f"[Groq] خطأ: {e} — سيُرسل التقرير الخام")
            return raw_data

    # ─────────────────────────────────────────────────
    # بناء البيانات الخام للـ AI
    # ─────────────────────────────────────────────────
    def _build_raw_data(self, all_courses: list[dict], new_items_map: dict) -> str:
        now       = datetime.now().strftime("%A %d/%m/%Y الساعة %H:%M")
        total_new = sum(len(v) for d in new_items_map.values() for v in d.values())

        raw  = f"التاريخ والوقت: {now}\n"
        raw += f"عدد المساقات المراقبة: {len(all_courses)}\n"
        raw += f"إجمالي العناصر الجديدة: {total_new}\n\n"

        CATS = {
            "resources":    "ملفات ومحاضرات",
            "assignments":  "واجبات",
            "quizzes":      "اختبارات وكويزات",
            "forums":       "منتديات",
            "wikis":        "ويكيات",
            "weekly_items": "روابط وأنشطة",
            "others":       "أخرى",
        }

        for course in all_courses:
            cid   = course["course_id"]
            cname = course["course_name"]
            curl  = course.get("url", "")
            cnew  = new_items_map.get(cid, {})

            raw += f"{'═'*40}\n"
            raw += f"المساق: {cname}\n"
            raw += f"رابط المساق: {curl}\n"

            # ── الجديد ──
            if cnew:
                raw += "\n[[ عناصر جديدة في هذا المساق ]]\n"
                for cat, items in cnew.items():
                    cat_label = CATS.get(cat, cat)
                    raw += f"نوع: {cat_label}\n"
                    for item in items:
                        raw += f"  الاسم: {item['name']}\n"
                        raw += f"  الرابط: {item['url']}\n"
                        if item.get("date"):
                            raw += f"  الموعد: {item['date']}\n"
                        if item.get("status") and item["status"] not in ["-", ""]:
                            raw += f"  الحالة: {item['status']}\n"
                        raw += "\n"
            else:
                raw += "\n[[ لا يوجد جديد في هذا المساق ]]\n"

            # ── القديم ──
            has_old = False
            for cat, label in CATS.items():
                items = course.get(cat, [])
                new_ids = {x["id"] for x in cnew.get(cat, [])}
                old = [i for i in items if i["id"] not in new_ids]
                if old:
                    if not has_old:
                        raw += "\n[[ المحتوى الموجود مسبقاً ]]\n"
                        has_old = True
                    raw += f"نوع: {label}\n"
                    for item in old:
                        raw += f"  الاسم: {item['name']}\n"
                        raw += f"  الرابط: {item['url']}\n"
                        if item.get("date"):
                            raw += f"  الموعد: {item['date']}\n"

            raw += "\n"

        return raw

    # ─────────────────────────────────────────────────
    # التقرير الكامل
    # ─────────────────────────────────────────────────
    def send_full_report(self, all_courses: list[dict], new_items_map: dict):
        raw_data = self._build_raw_data(all_courses, new_items_map)
        report   = self._generate_report(raw_data)
        self._dispatch(report)

    # ─────────────────────────────────────────────────
    # رسائل النظام
    # ─────────────────────────────────────────────────
    def send_test(self) -> bool:
        return self.send(
            "✅ *Moodle Tracker يعمل!*\n"
            "🎓 جامعة الأقصى — سيبدأ المراقبة الآن 🚀"
        )

    def send_error(self, msg: str):
        self.send(f"⚠️ *خطأ في Moodle Tracker*\n`{msg}`")

    # ─────────────────────────────────────────────────
    # تقسيم وإرسال الرسائل الطويلة
    # ─────────────────────────────────────────────────
    def _dispatch(self, text: str, limit: int = 4000):
        if len(text) <= limit:
            self.send(text)
            return
        lines   = text.split("\n")
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > limit:
                if current.strip():
                    self.send(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current.strip():
            self.send(current)
