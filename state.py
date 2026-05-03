import json, os
from config import STATE_FILE

TRACKED = ["quizzes", "assignments", "resources", "forums", "wikis", "weekly_items", "others"]


def load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def find_new(course: dict, old: dict) -> dict:
    cid = course["course_id"]
    old_course = old.get(cid, {})
    new = {}
    for cat in TRACKED:
        old_ids = set(i["id"] if isinstance(i, dict) else i
                      for i in old_course.get(cat, []))
        fresh = [i for i in course.get(cat, []) if i["id"] not in old_ids]
        if fresh:
            new[cat] = fresh
    return new


def build_state(all_courses: list[dict]) -> dict:
    state = {}
    for c in all_courses:
        cid = c["course_id"]
        state[cid] = {
            "course_name": c.get("course_name", ""),
            "url":         c.get("url", ""),
        }
        for cat in TRACKED:
            state[cid][cat] = c.get(cat, [])
    return state
