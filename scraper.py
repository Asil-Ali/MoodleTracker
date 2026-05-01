"""
scraper.py — سكرابر مبني على هيكل moodle.alaqsa.edu.ps الفعلي
"""

import re
import requests
from bs4 import BeautifulSoup


class MoodleScraper:
    def __init__(self, base_url: str, username: str, password: str):
        self.base   = base_url.rstrip("/")
        self.user   = username
        self.pwd    = password
        self.s      = requests.Session()
        self.s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13) "
                "AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
            )
        })

    # ─────────────────────────────────────────────────
    # 1. تسجيل الدخول
    # ─────────────────────────────────────────────────
    def login(self) -> tuple[bool, str]:
        try:
            login_url = f"{self.base}/login/index.php"
            r = self.s.get(login_url, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            # استخراج logintoken
            token_tag = soup.find("input", {"name": "logintoken"})
            token = token_tag["value"] if token_tag else ""

            r = self.s.post(login_url, data={
                "username":   self.user,
                "password":   self.pwd,
                "logintoken": token,
                "anchor":     "",
            }, timeout=30)

            # التحقق من نجاح الدخول
            if "loginerrormessage" in r.text or "/login/index.php" in r.url:
                return False, "❌ فشل تسجيل الدخول — تحقق من رقم الطالب وكلمة المرور"

            return True, "✅ تم تسجيل الدخول"

        except requests.ConnectionError:
            return False, "❌ لا يوجد اتصال بالإنترنت أو الموقع غير متاح"
        except Exception as e:
            return False, f"❌ خطأ: {e}"

    # ─────────────────────────────────────────────────
    # 2. جلب قائمة المساقات
    # ─────────────────────────────────────────────────
    def get_courses(self) -> list[dict]:
        """
        تجيب قائمة المساقات من صفحة "مقرراتي الدراسية"
        بناءً على الصور: الكورسات في /my/ أو صفحة خاصة
        """
        courses = []
        seen = set()

        # نجرب الصفحتين الممكنتين
        for url in [f"{self.base}/my/", f"{self.base}/"]:
            try:
                r = self.s.get(url, timeout=30)
                soup = BeautifulSoup(r.text, "html.parser")

                # كل رابط فيه /course/view.php?id=
                for a in soup.find_all("a", href=re.compile(r"/course/view\.php\?id=\d+")):
                    href = a["href"]
                    m = re.search(r"id=(\d+)", href)
                    if not m:
                        continue
                    cid = m.group(1)
                    if cid in seen:
                        continue
                    seen.add(cid)

                    name = a.get_text(strip=True)
                    # تجاهل الروابط الفارغة أو القصيرة جداً
                    if len(name) < 4:
                        continue

                    courses.append({
                        "id":   cid,
                        "name": name,
                        "url":  f"{self.base}/course/view.php?id={cid}",
                    })

                if courses:
                    break

            except Exception as e:
                print(f"[scraper] خطأ في جلب المساقات من {url}: {e}")

        return courses

    # ─────────────────────────────────────────────────
    # 3. جلب محتوى مساق (المقرر الأسبوعي + النشاطات)
    # ─────────────────────────────────────────────────
    def get_course_content(self, course_id: str, course_name: str) -> dict:
        content = {
            "course_id":   course_id,
            "course_name": course_name,
            "url":         f"{self.base}/course/view.php?id={course_id}",
            # من تاب المقرر
            "weekly_items": [],   # كل العناصر الأسبوعية (روابط + ملفات)
            # من تاب النشاطات
            "quizzes":     [],
            "assignments": [],
            "resources":   [],
            "forums":      [],
            "wikis":       [],
            "others":      [],
        }

        # ── 3a. تاب المقرر (محتوى أسبوعي) ──────────
        self._scrape_course_tab(content)

        # ── 3b. تاب النشاطات (منظم بالنوع مع تواريخ) ──
        self._scrape_activities_tab(content)

        return content

    # ─────────────────────────────────────────────────
    # 3a. تاب المقرر
    # ─────────────────────────────────────────────────
    def _scrape_course_tab(self, content: dict):
        try:
            r = self.s.get(content["url"], timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            # الأقسام الأسبوعية: section أو li.section
            sections = soup.find_all(
                lambda tag: tag.name in ["li", "div"] and
                any("section" in c for c in tag.get("class", []))
            )

            # لو مفيش sections نرجع لجلب كل الروابط
            if not sections:
                sections = [soup]

            for sec in sections:
                # اسم القسم (الأسبوع)
                sec_title = ""
                title_tag = sec.find(class_=re.compile(r"sectionname|section-title"))
                if title_tag:
                    sec_title = title_tag.get_text(strip=True)

                # كل الروابط داخل القسم
                for a in sec.find_all("a", href=re.compile(r"/mod/")):
                    href = a["href"]
                    name = a.get_text(strip=True)
                    if not name or len(name) < 2:
                        continue

                    mod_type = self._mod_type_from_url(href)
                    item_id  = re.search(r"id=(\d+)", href)
                    iid      = item_id.group(1) if item_id else href

                    content["weekly_items"].append({
                        "id":      f"w_{iid}",
                        "name":    name,
                        "url":     href,
                        "type":    mod_type,
                        "section": sec_title,
                    })

        except Exception as e:
            print(f"[scraper] خطأ في تاب المقرر لـ '{content['course_name']}': {e}")

    # ─────────────────────────────────────────────────
    # 3b. تاب النشاطات — المصدر الذهبي للتواريخ
    # ─────────────────────────────────────────────────
    def _scrape_activities_tab(self, content: dict):
        """
        صفحة النشاطات في Moodle تعطي كل الأنشطة مرتبة بنوعها
        مع تواريخ الاستحقاق وحالة التسليم
        URL المعتادة: /course/view.php?id=X&view=activities
        أو: /mod/assign/index.php?id=X للواجبات
        """
        cid = content["course_id"]

        # نجرب عدة URLs ممكنة لصفحة النشاطات
        activity_urls = [
            f"{self.base}/course/view.php?id={cid}&view=activities",
            f"{self.base}/course/view.php?id={cid}#activities",
        ]

        for url in activity_urls:
            try:
                r = self.s.get(url, timeout=30)
                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "html.parser")
                self._parse_activities_page(soup, content)
                break

            except Exception as e:
                print(f"[scraper] خطأ في تاب النشاطات: {e}")

        # جلب الواجبات مباشرة (أكثر موثوقية)
        self._scrape_assignments_direct(content)
        # جلب الكويزات مباشرة
        self._scrape_quizzes_direct(content)

    def _parse_activities_page(self, soup: BeautifulSoup, content: dict):
        """يحلل صفحة النشاطات ويستخرج كل أنواع الأنشطة"""

        # بحث عن الجداول أو البطاقات المنظمة حسب نوع النشاط
        # بناءً على صورة 7: إختبارات، الموارد، منتديات، واجبات، ويكيات

        type_map = {
            "quiz":   "quizzes",
            "assign": "assignments",
            "resource": "resources",
            "forum":  "forums",
            "wiki":   "wikis",
        }

        for a in soup.find_all("a", href=re.compile(r"/mod/(quiz|assign|resource|forum|wiki)/")):
            href     = a["href"]
            mod_type = self._mod_type_from_url(href)
            cat      = type_map.get(mod_type, "others")
            name     = a.get_text(strip=True)
            if not name or len(name) < 2:
                continue

            item_id = re.search(r"id=(\d+)", href)
            iid = item_id.group(1) if item_id else href

            # استخراج التاريخ من العنصر الأب
            parent = a.find_parent(["tr", "li", "div"])
            date_str = self._extract_date(parent) if parent else ""

            item = {
                "id":   f"a_{iid}",
                "name": name,
                "url":  href,
                "date": date_str,
            }

            # تجنب التكرار
            existing_ids = {i["id"] for i in content[cat]}
            if item["id"] not in existing_ids:
                content[cat].append(item)

    def _scrape_assignments_direct(self, content: dict):
        """
        يجيب الواجبات من صفحتها المخصصة
        بناءً على صورة 10: الاسم، تاريخ الاستحقاق، حالة التسليم
        """
        cid = content["course_id"]
        url = f"{self.base}/mod/assign/index.php?id={cid}"
        try:
            r = self.s.get(url, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            existing_ids = {i["id"] for i in content["assignments"]}

            for row in soup.find_all("tr"):
                a_tag = row.find("a", href=re.compile(r"/mod/assign/view\.php"))
                if not a_tag:
                    continue

                href = a_tag["href"]
                name = a_tag.get_text(strip=True)
                mid  = re.search(r"id=(\d+)", href)
                iid  = mid.group(1) if mid else href

                if f"d_{iid}" in existing_ids:
                    continue

                cells = row.find_all("td")
                due_date   = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                status     = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                content["assignments"].append({
                    "id":     f"d_{iid}",
                    "name":   name,
                    "url":    href,
                    "date":   due_date,
                    "status": status,
                })

        except Exception as e:
            print(f"[scraper] خطأ في جلب الواجبات المباشر: {e}")

    def _scrape_quizzes_direct(self, content: dict):
        """
        يجيب الكويزات من صفحتها المخصصة
        بناءً على صورة 7: الاسم، تاريخ البداية والنهاية، الدرجة
        """
        cid = content["course_id"]
        url = f"{self.base}/mod/quiz/index.php?id={cid}"
        try:
            r = self.s.get(url, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            existing_ids = {i["id"] for i in content["quizzes"]}

            for row in soup.find_all("tr"):
                a_tag = row.find("a", href=re.compile(r"/mod/quiz/view\.php"))
                if not a_tag:
                    continue

                href = a_tag["href"]
                name = a_tag.get_text(strip=True)
                mid  = re.search(r"id=(\d+)", href)
                iid  = mid.group(1) if mid else href

                if f"q_{iid}" in existing_ids:
                    continue

                cells    = row.find_all("td")
                date_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                grade    = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                content["quizzes"].append({
                    "id":    f"q_{iid}",
                    "name":  name,
                    "url":   href,
                    "date":  date_str,
                    "grade": grade,
                })

        except Exception as e:
            print(f"[scraper] خطأ في جلب الكويزات المباشر: {e}")

    # ─────────────────────────────────────────────────
    # مساعدات
    # ─────────────────────────────────────────────────
    def _mod_type_from_url(self, url: str) -> str:
        m = re.search(r"/mod/(\w+)/", url)
        return m.group(1) if m else "other"

    def _extract_date(self, tag) -> str:
        if not tag:
            return ""
        text = tag.get_text(" ", strip=True)
        # ابحث عن نمط تاريخ عربي أو إنجليزي
        patterns = [
            r"\d{1,2}\s+(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)",
            r"(?:الجمعة|السبت|الأحد|الاثنين|الثلاثاء|الأربعاء|الخميس)[،,\s]+\d+",
            r"\d{1,2}/\d{1,2}/\d{4}",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(0)
        return ""
