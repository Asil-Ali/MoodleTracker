"""
main.py ← شغّلي هذا الملف فقط
"""
import sys, time
from datetime import datetime
from config   import MOODLE_BASE_URL, STUDENT_ID, PASSWORD, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, CHECK_INTERVAL_HOURS
from scraper  import MoodleScraper
from notifier import TelegramNotifier
from state    import load, save, find_new, build_state


def run(scraper: MoodleScraper, notifier: TelegramNotifier):
    print(f"\n[{datetime.now():%H:%M:%S}] 🔍 بدء الفحص...")

    ok, msg = scraper.login()
    print(f"  {msg}")
    if not ok:
        notifier.send_error(msg)
        return

    courses = scraper.get_courses()
    if not courses:
        notifier.send_error("لم أجد أي مساقات — تحقق من الإعدادات")
        return
    print(f"  📚 {len(courses)} مساق")

    all_data = []
    for c in courses:
        print(f"  📖 {c['name']}")
        data = scraper.get_course_content(c["id"], c["name"])
        all_data.append(data)

    old   = load()
    new_map = {}
    for d in all_data:
        n = find_new(d, old)
        if n:
            new_map[d["course_id"]] = n
            total = sum(len(v) for v in n.values())
            print(f"    🔔 {total} جديد في: {d['course_name']}")

    notifier.send_full_report(all_data, new_map)
    save(build_state(all_data))

    total_new = sum(len(v) for d in new_map.values() for v in d.values())
    print(f"  ✅ انتهى — {total_new} عنصر جديد")


def main():
    print("="*50)
    print("  🎓 Moodle Tracker | جامعة الأقصى")
    print("="*50)

    scraper  = MoodleScraper(MOODLE_BASE_URL, STUDENT_ID, PASSWORD)
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

    if "--test" in sys.argv:
        print("\n🧪 اختبار Telegram...")
        print("✅ يعمل!" if notifier.send_test() else "❌ فشل الاتصال")
        return

    run(scraper, notifier)

    interval = CHECK_INTERVAL_HOURS * 3600
    print(f"\n⏰ الفحص التالي بعد {CHECK_INTERVAL_HOURS} ساعة (Ctrl+C للإيقاف)")
    while True:
        try:
            time.sleep(interval)
            run(scraper, notifier)
        except KeyboardInterrupt:
            print("\n👋 تم الإيقاف")
            break
        except Exception as e:
            print(f"[خطأ] {e}")
            notifier.send_error(str(e))
            time.sleep(300)


if __name__ == "__main__":
    main()
