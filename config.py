# =============================================
#   إعدادات Moodle Tracker - جامعة الأقصى
# =============================================

# --- Moodle مباشرة (مش البوابة) ---
MOODLE_BASE_URL = "https://moodle.alaqsa.edu.ps"

# --- بيانات الدخول (نفس اللي بتدخلي فيها Moodle مباشرة) ---
STUDENT_ID = "YOUR_STUDENT_NUMBER"   # رقمك الجامعي
PASSWORD   = "YOUR_PASSWORD"         # كلمة المرور

# --- Telegram Bot ---
TELEGRAM_TOKEN   = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# --- إعدادات الفحص ---
CHECK_INTERVAL_HOURS = 6    # كل كم ساعة يفحص (6 = أربع مرات باليوم)

# --- ملف الحالة (لا تحذفيه) ---
STATE_FILE = "state.json"
