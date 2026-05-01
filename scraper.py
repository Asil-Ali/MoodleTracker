"""
scraper.py — يستخدم Moodle Web Services API مباشرة
أسرع وأضمن من HTML scraping
"""

import requests


class MoodleScraper:
    def __init__(self, base_url: str, username: str, password: str):
        self.base    = base_url.rstrip("/")
        self.user    = username
        self.pwd     = password
        self.token   = None
        self.s       = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0"})
        self.api_url = f"{self.base}/webservice/rest/server.php"

    def login(self) -> tuple[bool, str]:
        try:
            r = self.s.post(f"{self.base}/login/token.php", data={
                "username": self.user,
                "password": self.pwd,
                "service":  "moodle_mobile_app",
            }, timeout=30)
            data = r.json()
            if "token" in data:
                self.token = data["token"]
                return True, "✅ تم تسجيل الدخول"
            msg = data.get("error", data.get("message", "خطأ غير معروف"))
            return False, f"❌ فشل: {msg}"
        except requests.ConnectionError:
            return False, "❌ لا يوجد اتصال"
        except Exception as e:
            return False, f"❌ خطأ: {e}"

    def _call(self, function: str, **params):
        try:
            r = self.s.post(self.api_url, data={
                "wstoken":            self.token,
                "wsfunction":         function,
                "moodlewsrestformat": "json",
                **params,
            }, timeout=30)
            return r.json()
        except Exception as e:
            print(f"[API] {function}: {e}")
            return None

    def get_courses(self) -> list[dict]:
        info = self._call("core_webservice_get_site_info")
        uid  = info.get("userid") if isinstance(info, dict) else None
        courses_raw = []

        if uid:
            result = self._call("core_enrol_get_users_courses", userid=uid)
            if isinstance(result, list):
                courses_raw = result

        if not courses_raw:
            result = self._call(
                "core_course_get_enrolled_courses_by_timeline_classification",
                classification="all", limit=50, offset=0, sort="fullname"
            )
            if isinstance(result, dict):
                courses_raw = result.get("courses", [])

        courses = []
        for c in courses_raw:
            cid  = str(c.get("id", ""))
            name = c.get("fullname", c.get("shortname", ""))
            if cid and name:
                courses.append({
                    "id":   cid,
                    "name": name,
                    "url":  f"{self.base}/course/view.php?id={cid}",
                })
        return courses

    def get_course_content(self, course_id: str, course_name: str) -> dict:
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
        self._scrape_contents(content, course_id)
        self._scrape_assignments(content, course_id)
        self._scrape_quizzes(content, course_id)
        return content

    def _scrape_contents(self, content: dict, course_id: str):
        result = self._call("core_course_get_contents", courseid=course_id)
        if not isinstance(result, list):
            return
        for section in result:
            sec_name = section.get("name", "")
            for mod in section.get("modules", []):
                mod_type = mod.get("modname", "other")
                name     = mod.get("name", "")
                mid      = str(mod.get("id", ""))
                url      = mod.get("url", f"{self.base}/mod/{mod_type}/view.php?id={mid}")
                item = {"id": f"m_{mid}", "name": name, "url": url, "type": mod_type, "section": sec_name}
                if mod_type in ("resource", "url", "page", "folder"):
                    content["resources"].append(item)
                elif mod_type in ("forum", "hsuforum"):
                    content["forums"].append(item)
                elif mod_type == "wiki":
                    content["wikis"].append(item)
                elif mod_type not in ("quiz", "assign", "label"):
                    content["weekly_items"].append(item)

    def _scrape_assignments(self, content: dict, course_id: str):
        result = self._call("mod_assign_get_assignments", **{"courseids[0]": course_id})
        if not isinstance(result, dict):
            return
        for course in result.get("courses", []):
            for a in course.get("assignments", []):
                aid  = str(a.get("id", ""))
                cmid = str(a.get("cmid", ""))
                due  = a.get("duedate", 0)
                content["assignments"].append({
                    "id":     f"a_{aid}",
                    "name":   a.get("name", ""),
                    "url":    f"{self.base}/mod/assign/view.php?id={cmid}",
                    "date":   self._ts(due) if due else "",
                    "status": "",
                })

    def _scrape_quizzes(self, content: dict, course_id: str):
        result = self._call("mod_quiz_get_quizzes_by_courses", **{"courseids[0]": course_id})
        if not isinstance(result, dict):
            return
        for q in result.get("quizzes", []):
            qid  = str(q.get("id", ""))
            cmid = str(q.get("coursemodule", ""))
            close = q.get("timeclose", 0)
            content["quizzes"].append({
                "id":    f"q_{qid}",
                "name":  q.get("name", ""),
                "url":   f"{self.base}/mod/quiz/view.php?id={cmid}",
                "date":  self._ts(close) if close else "",
                "grade": "",
            })

    def _ts(self, ts: int) -> str:
        from datetime import datetime
        try:
            return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
        except:
            return ""
