"""
scraper.py — HTML scraper مع IDs ثابتة
"""
import re
import requests
from bs4 import BeautifulSoup

# ── IDs المساقات الحقيقية ──────────────────────
COURSE_IDS = [2363, 2834, 2730, 2727, 2271, 2270, 2247, 2153]


class MoodleScraper:
    def __init__(self, base_url, username, password):
        self.base = base_url.rstrip("/")
        self.user = username
        self.pwd  = password
        self.s    = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0"})

    # ─────────────────────────────────────────────
    # 1. تسجيل الدخول
    # ─────────────────────────────────────────────
    def login(self):
        try:
            login_url = f"{self.base}/login/index.php"
            r    = self.s.get(login_url, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            tag  = soup.find("input", {"name": "logintoken"})
            token = tag["value"] if tag else ""

            r = self.s.post(login_url, data={
                "username":   self.user,
                "password":   self.pwd,
                "logintoken": token,
                "anchor":     "",
            }, timeout=30)

            if "loginerrormessage" in r.text or r.url.endswith("login/index.php"):
                return False, "❌ فشل تسجيل الدخول"
            return True, "✅ تم تسجيل الدخول"

        except requests.ConnectionError:
            return False, "❌ لا يوجد اتصال"
        except Exception as e:
            return False, f"❌ خطأ: {e}"

    # ─────────────────────────────────────────────
    # 2. المساقات من IDs الثابتة
    # ─────────────────────────────────────────────
    def get_courses(self):
        courses = []
        for cid in COURSE_IDS:
            try:
                url  = f"{self.base}/course/view.php?id={cid}"
                r    = self.s.get(url, timeout=30)
                soup = BeautifulSoup(r.text, "html.parser")

                # اسم المساق من العنوان
                h1 = soup.find("h1")
                name = h1.get_text(strip=True) if h1 else f"مساق {cid}"

                courses.append({
                    "id":   str(cid),
                    "name": name,
                    "url":  url,
                })
                print(f"    ✅ {name}")
            except Exception as e:
                print(f"    ⚠️ مساق {cid}: {e}")

        return courses

    # ─────────────────────────────────────────────
    # 3. محتوى مساق واحد من تاب النشاطات
    # ─────────────────────────────────────────────
    def get_course_content(self, course_id, course_name):
        content = {
            "course_id":    course_id,
            "course_name":  course_name,
            "url":          f"{self.base}/course/view.php?id={course_id}",
            "weekly_items": [],
            "quizzes":      [],
            "assignments":  [],
            "resources":    [],
            "forums":       [],
            "wikis":        [],
            "others":       [],
        }

        self._scrape_course_page(content, course_id)
        self._scrape_assign_index(content, course_id)
        self._scrape_quiz_index(content, course_id)

        return content

    # ─────────────────────────────────────────────
    # 3a. صفحة المقرر الأسبوعية
    # ─────────────────────────────────────────────
    def _scrape_course_page(self, content, course_id):
        try:
            url  = f"{self.base}/course/view.php?id={course_id}"
            r    = self.s.get(url, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a", href=re.compile(r"/mod/")):
                href     = a["href"]
                mod_type = self._mod_type(href)
                if mod_type in ("quiz", "assign"):
                    continue

                name = a.get_text(strip=True)
                if not name or len(name) < 2:
                    continue

                mid = re.search(r"id=(\d+)", href)
                iid = f"w_{mid.group(1)}" if mid else f"w_{href[-6:]}"

                item = {"id": iid, "name": name, "url": href, "type": mod_type}

                if mod_type in ("resource", "url", "page", "folder"):
                    if not any(i["id"] == iid for i in content["resources"]):
                        content["resources"].append(item)
                elif mod_type in ("forum", "hsuforum"):
                    if not any(i["id"] == iid for i in content["forums"]):
                        content["forums"].append(item)
                elif mod_type == "wiki":
                    if not any(i["id"] == iid for i in content["wikis"]):
                        content["wikis"].append(item)
                else:
                    if not any(i["id"] == iid for i in content["weekly_items"]):
                        content["weekly_items"].append(item)

        except Exception as e:
            print(f"[scraper] خطأ في صفحة المقرر {course_id}: {e}")

    # ─────────────────────────────────────────────
    # 3b. قائمة الواجبات المباشرة
    # ─────────────────────────────────────────────
    def _scrape_assign_index(self, content, course_id):
        try:
            url  = f"{self.base}/mod/assign/index.php?id={course_id}"
            r    = self.s.get(url, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            for row in soup.find_all("tr"):
                a_tag = row.find("a", href=re.compile(r"/mod/assign/view\.php"))
                if not a_tag:
                    continue

                href  = a_tag["href"]
                name  = a_tag.get_text(strip=True)
                mid   = re.search(r"id=(\d+)", href)
                iid   = f"d_{mid.group(1)}" if mid else f"d_{href[-6:]}"

                if any(i["id"] == iid for i in content["assignments"]):
                    continue

                cells    = row.find_all("td")
                due_date = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                status   = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                content["assignments"].append({
                    "id":     iid,
                    "name":   name,
                    "url":    href,
                    "date":   due_date,
                    "status": status,
                })
        except Exception as e:
            print(f"[scraper] خطأ في الواجبات {course_id}: {e}")

    # ─────────────────────────────────────────────
    # 3c. قائمة الكويزات المباشرة
    # ─────────────────────────────────────────────
    def _scrape_quiz_index(self, content, course_id):
        try:
            url  = f"{self.base}/mod/quiz/index.php?id={course_id}"
            r    = self.s.get(url, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")

            for row in soup.find_all("tr"):
                a_tag = row.find("a", href=re.compile(r"/mod/quiz/view\.php"))
                if not a_tag:
                    continue

                href = a_tag["href"]
                name = a_tag.get_text(strip=True)
                mid  = re.search(r"id=(\d+)", href)
                iid  = f"q_{mid.group(1)}" if mid else f"q_{href[-6:]}"

                if any(i["id"] == iid for i in content["quizzes"]):
                    continue

                cells = row.find_all("td")
                date  = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                grade = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                content["quizzes"].append({
                    "id":    iid,
                    "name":  name,
                    "url":   href,
                    "date":  date,
                    "grade": grade,
                })
        except Exception as e:
            print(f"[scraper] خطأ في الكويزات {course_id}: {e}")

    def _mod_type(self, url):
        m = re.search(r"/mod/(\w+)/", url)
        return m.group(1) if m else "other"
