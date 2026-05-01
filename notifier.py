"""
notifier.py — يبني رسائل Telegram منظمة وأنيقة
مبنية على هيكل moodle.alaqsa.edu.ps الفعلي
"""

import requests
from datetime import datetime

API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.api     = API_URL.format(token=token)

    # ─────────────────────────────────────────────────
    # إرسال رسالة
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
    # تقرير كامل
    # ─────────────────────────────────────────────────
    def send_full_report(self, all_courses: list[dict], new_items_map: dict):
        now = datetime.now().strftime("%A %d/%m/%Y ─ %H:%M")

        total_new = sum(
            len(v) for d in new_items_map.values() for v in d.values()
        )

        # ── الرأس ──────────────────────────────────
        if total_new:
            header = (
                f"🎓 *جامعة الأقصى | تحديث المساقات*\n"
                f"🕐 {now}\n"
                f"🔔 *{total_new} عنصر جديد!*\n"
            )
        else:
            header = (
                f"🎓 *جامعة الأقصى | تقرير المساقات*\n"
                f"🕐 {now}\n"
                f"✅ لا يوجد جديد منذ آخر فحص\n"
            )

        messages = [header]

        # ── قسم لكل مساق ───────────────────────────
        for course in all_courses:
            cid  = course["course_id"]
            cnew = new_items_map.get(cid, {})
            block = self._build_course_block(course, cnew)
            if block:
                messages.append(block)

        self._dispatch(messages)

    # ─────────────────────────────────────────────────
    # بناء بلوك مساق واحد
    # ─────────────────────────────────────────────────
    def _build_course_block(self, course: dict, cnew: dict) -> str:
        name = course["course_name"]
        url  = course.get("url", "")
        lines = []

        lines.append(f"\n{'━'*22}")
        lines.append(f"📖 *{name}*")
        if url:
            lines.append(f"🔗 [فتح المساق]({url})")

        # ── الجديد ──
        if cnew:
            lines.append("\n🆕 *جديد:*")
            for cat, items in cnew.items():
                icon = self._icon(cat)
                for item in items:
                    n   = item["name"]
                    u   = item["url"]
                    d   = item.get("date", "")
                    st  = item.get("status", "")
                    gr  = item.get("grade", "")

                    row = f"  {icon} [{n}]({u})"
                    if d:  row += f" ⏰ {d}"
                    if st and st not in ["-", "لا تسليم"]: row += f" ── {st}"
                    if gr and gr != "-": row += f" 📊 {gr}"
                    lines.append(row)

        # ── الواجبات القائمة ──
        assignments = course.get("assignments", [])
        if assignments:
            lines.append("\n📝 *الواجبات:*")
            new_a_ids = {i["id"] for i in cnew.get("assignments", [])}
            for a in assignments:
                status = a.get("status", "")
                date   = a.get("date", "")
                n, u   = a["name"], a["url"]
                flag   = "🆕 " if a["id"] in new_a_ids else ""
                row    = f"  {flag}📝 [{n}]({u})"
                if date: row += f" ⏰ {date}"
                if status and status not in ["-"]:
                    submitted = "لا تسليم" not in status
                    row += f" {'✅' if submitted else '❌'}"
                lines.append(row)

        # ── الكويزات القائمة ──
        quizzes = course.get("quizzes", [])
        if quizzes:
            lines.append("\n🎯 *الاختبارات:*")
            new_q_ids = {i["id"] for i in cnew.get("quizzes", [])}
            for q in quizzes:
                date  = q.get("date", "")
                grade = q.get("grade", "")
                n, u  = q["name"], q["url"]
                flag  = "🆕 " if q["id"] in new_q_ids else ""
                row   = f"  {flag}🎯 [{n}]({u})"
                if date:  row += f" 📅 {date}"
                if grade and grade != "-": row += f" 📊 {grade}"
                lines.append(row)

        # ── الموارد (ملخص) ──
        resources = course.get("resources", [])
        weekly    = course.get("weekly_items", [])
        all_res   = resources + [w for w in weekly if w.get("type") in ("resource", "url")]

        if all_res:
            new_r_ids = {i["id"] for i in cnew.get("resources", [])} | \
                        {i["id"] for i in cnew.get("weekly_items", [])}
            new_count = len([r for r in all_res if r["id"] in new_r_ids])
            total_res = len(all_res)
            label = f"📎 *الموارد:* {total_res} عنصر"
            if new_count:
                label += f" ({'🆕 ' + str(new_count) + ' جديد'})"
            lines.append(f"\n{label}")

            # اعرض الجديد بالاسم
            for r in all_res:
                if r["id"] in new_r_ids:
                    lines.append(f"  🆕 📎 [{r['name']}]({r['url']})")

        if len(lines) <= 3:  # بس الرأس
            return ""

        return "\n".join(lines)

    # ─────────────────────────────────────────────────
    # رسالة اختبار
    # ─────────────────────────────────────────────────
    def send_test(self) -> bool:
        return self.send(
            "✅ *Moodle Tracker يعمل!*\n"
            "🎓 جامعة الأقصى — `moodle.alaqsa.edu.ps`\n"
            "سيبدأ المراقبة التلقائية الآن 🚀"
        )

    def send_error(self, msg: str):
        self.send(f"⚠️ *خطأ في Moodle Tracker*\n```\n{msg}\n```")

    # ─────────────────────────────────────────────────
    # مساعدات
    # ─────────────────────────────────────────────────
    def _icon(self, cat: str) -> str:
        return {
            "quizzes":     "🎯",
            "assignments": "📝",
            "resources":   "📎",
            "forums":      "💬",
            "wikis":       "📋",
            "weekly_items":"🔗",
            "others":      "📌",
        }.get(cat, "📌")

    def _dispatch(self, parts: list[str], limit: int = 4000):
        """يقسم الرسائل الطويلة ويبعثها"""
        current = ""
        for part in parts:
            if len(current) + len(part) > limit:
                if current.strip():
                    self.send(current)
                current = part
            else:
                current += "\n" + part
        if current.strip():
            self.send(current)
