import os

# =============================================
#   إعدادات Moodle Tracker - جامعة الأقصى
# =============================================

# --- Moodle مباشرة (مش البوابة) ---
MOODLE_BASE_URL = "https://moodle.alaqsa.edu.ps"

# --- بيانات الدخول من متغيرات البيئة ---
STUDENT_ID = os.environ.get("MOODLE_USER", "")
PASSWORD   = os.environ.get("MOODLE_PASS", "")

# --- Telegram Bot ---
TELEGRAM_TOKEN   = os.environ.get("TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# --- إعدادات الفحص ---
CHECK_INTERVAL_HOURS = 6    # كل كم ساعة يفحص

# --- ملف الحالة (لا تحذفيه) ---
STATE_FILE = "state.json"
