import os

# =============================================
#   إعدادات Moodle Tracker - جامعة الأقصى
#   آمن للرفع على GitHub ✅
# =============================================

# --- Moodle ---
MOODLE_BASE_URL  = "https://moodle.alaqsa.edu.ps"
STUDENT_ID       = os.environ.get("MOODLE_USER", "")
PASSWORD         = os.environ.get("MOODLE_PASS", "")

# --- Telegram ---
TELEGRAM_TOKEN   = os.environ.get("TG_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# --- Groq AI ---
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")

# --- إعدادات ---
CHECK_INTERVAL_HOURS = 6
STATE_FILE = "state.json"
