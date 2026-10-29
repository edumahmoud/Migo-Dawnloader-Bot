"""نقطة دخول Vercel — البوت في وضع الويبهوك (ASGI)

- GET  /api            → فحص صحة البوت (لو فيه عطب بيقول السبب بالتفصيل)
- GET  /api?key=TOKEN  → تفعيل الويبهوك (تتصل مرة واحدة بعد النشر)
- POST /api            → تحديثات تليجرام
"""
import asyncio
import hashlib
import json
import os
import traceback

# إعدادات مناسبة لحدود Vercel (60 ثانية + قراءة فقط)
os.environ.setdefault("FFMPEG_DIR", "/tmp/ffmpeg")
os.environ.setdefault("MAX_FILE_MB", "25")

# الاستيرادات الثقيلة محميّة عمداً — لو أي مكتبة ناقصة أو أي حاجة قفلت وقت التحميل،
# الصفحة نفسها هترجّع سبب العطل بالتفصيل بدل صفحة 500 الغامضة من فيرسيل
_boot_error = None
try:
    import config  # noqa: E402
    import handlers  # noqa: E402
    from bot import register_handlers  # noqa: E402
    from downloader import ensure_ffmpeg  # noqa: E402
    from telegram import Update  # noqa: E402
    from telegram.ext import Application  # noqa: E402
except Exception:  # noqa: BLE001
    _boot_error = traceback.format_exc()

application = None
_app_lock = asyncio.Lock()


async def get_application():
    """بناء Application مرة واحدة لكل نسخة سيرفر حية"""
    global application
    if application is None:
        async with _app_lock:
            if application is None:
                config.validate()
                app = (
                    Application.builder()
                    .token(config.BOT_TOKEN)
                    .updater(None)  # من غير polling — الويبهوك فقط
                    .build()
                )
                register_handlers(app)
                await app.initialize()
                application = app
    return application


def _secret():
    return hashlib.sha256(config.BOT_TOKEN.encode()).hexdigest()[:32]


def _headers(scope):
    return {
        k.decode().lower(): v.decode("utf-8", "ignore")
        for k, v in scope.get("headers", [])
    }


async def _read_body(receive):
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body"):
            return body


async def _respond(send, status, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json; charset=utf-8")],
    })
    await send({"type": "http.response.body", "body": data})


async def app(scope, receive, send):
    if scope["type"] != "http":
        return
    method = scope.get("method", "GET").upper()
    path = scope.get("path", "/").rstrip("/")
    body = await _read_body(receive)

    # عطب في التحميل الأولي؟ نرجّع السبب كامل بدل ما فيرسيل يعرض صفحة 500 غامضة
    if _boot_error:
        await _respond(send, 500, {
            "error": "فشل تحميل موديولات البوت — ابعت الـ traceback ده للمطور:",
            "traceback": _boot_error[-2500:],
        })
        return

    # فحص الصحة + تفعيل الويبهوك
    if method == "GET" and path in ("", "/api", "/api/index"):
        from urllib.parse import parse_qs
        qs = parse_qs(scope.get("query_string", b"").decode("utf-8", "ignore"))
        if (qs.get("key") or [""])[0] == config.BOT_TOKEN:
            try:
                app_ = await get_application()
                host = _headers(scope).get("host", "")
                url = f"https://{host}/api"
                await app_.bot.set_webhook(
                    url=url,
                    secret_token=_secret(),
                    allowed_updates=["message", "callback_query"],
                    drop_pending_updates=True,
                )
                await app_.bot.set_my_commands(handlers.BOT_COMMANDS)
                await _respond(send, 200, {"webhook": url, "result": "تم تفعيل الويبهوك ✅"})
            except Exception as e:  # noqa: BLE001
                await _respond(send, 500, {"error": str(e)[:300]})
        else:
            await _respond(send, 200, {
                "status": "ok",
                "bot": "Migo Downloader 🤖",
                "hint": "افتح /api?key=توكن-البوت لتفعيل الويبهوك",
            })
        return

    # تحديثات تليجرام
    if method == "POST":
        if _headers(scope).get("x-telegram-bot-api-secret-token") != _secret():
            await _respond(send, 401, {"error": "unauthorized"})
            return
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:  # noqa: BLE001
            await _respond(send, 400, {"error": "bad json"})
            return
        try:
            app_ = await get_application()
            update = Update.de_json(data, app_.bot)
            if update is not None:
                await app_.process_update(update)
            await _respond(send, 200, {"ok": True})
        except Exception as e:  # noqa: BLE001
            await _respond(send, 500, {"error": str(e)[:300]})
        return

    await _respond(send, 404, {"error": "not found"})


# نبدأ تنزيل ffmpeg في الخلفية أول ما السيرفر يصحى (للدمج و MP3)
if os.getenv("VERCEL") and not _boot_error:
    import threading
    threading.Thread(target=ensure_ffmpeg, kwargs={"timeout": 120}, daemon=True).start()
