"""إعدادات البوت — بتتقرا من متغيرات البيئة أو ملف .env"""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


def _ids(raw):
    out = set()
    for part in (raw or "").replace(" ", "").split(","):
        if part.isdigit():
            out.add(int(part))
    return out


ADMIN_IDS = _ids(os.getenv("ADMIN_IDS", ""))
PANEL_KEY = os.getenv("PANEL_KEY", "").strip()  # مفتاح لوحة الإحصائيات على الموقع (لو فاضي: توكن البوت)
# حد تليجرام الحقيقي للبوتات = 50 ميجا للملف الواحد (50 * 1024 * 1024 بايت)
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "50") or 50)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "5") or 5)
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "30") or 30)
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3") or 3)
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt").strip()


def _chat_id(raw):
    """قراءة آيدي قناة/جروب من البيئة (زي -1001234567890) — بيرجع 0 لو مش صالح"""
    raw = (raw or "").strip()
    if raw.lstrip("-").isdigit():
        try:
            return int(raw)
        except ValueError:
            return 0
    return 0


# قناة التخزين الدائم للإحصائيات (اختياري — عشان الأرقام ماتتصفرش على Vercel)
STATS_CHAT_ID = _chat_id(os.getenv("STATS_CHAT_ID", ""))

DATA_DIR = os.getenv("DATA_DIR", "data")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")

try:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
except OSError:
    # بيئة قراءة فقط (زي Vercel) — نستخدم /tmp المؤقت
    DATA_DIR = "/tmp/migo-data"
    DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def validate():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise RuntimeError(
            "✋ مفيش توكن صحيح!\n"
            "1) هات التوكن من @BotFather (شوف README.md)\n"
            "2) حطه في متغيرات البيئة: BOT_TOKEN=123456:ABC-DEF\n"
            "3) على Vercel: Settings → Environment Variables → وبعدها اعمل Redeploy"
        )
