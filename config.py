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
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "48") or 48)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "5") or 5)
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "30") or 30)
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3") or 3)
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.txt").strip()
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
