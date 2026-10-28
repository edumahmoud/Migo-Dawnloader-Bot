#!/usr/bin/env python3
"""بوت تليجرام لتحميل الفيديوهات — نقطة التشغيل"""
import logging
import os
import threading

from telegram import BotCommand
from telegram.constants import ParseMode
from telegram.ext import (AIORateLimiter, ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, Defaults, MessageHandler, filters)

import config
import handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
log = logging.getLogger("bot")


def start_keepalive(port: int):
    """سيرفر HTTP صغير — عشان منصات الاستضافة المجانية تشوف البوت شغال"""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Bot is running ✅".encode())

        def log_message(self, *args):
            pass

    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        log.info("Keepalive HTTP server on port %s", port)
        server.serve_forever()
    except Exception as e:
        log.error("Keepalive server failed: %s", e)


async def post_init(app):
    me = await app.bot.get_me()
    handlers.BOT_USERNAME = me.username or ""
    await app.bot.set_my_commands([
        BotCommand("start", "تشغيل البوت"),
        BotCommand("help", "طريقة الاستخدام"),
        BotCommand("stats", "إحصائيات التحميل"),
    ])
    log.info("Bot started as @%s 🚀", me.username)


def main():
    config.validate()

    # لو فيه PORT (زي Railway/Render) — شغّل سيرفر صغير للفحص
    port = os.getenv("PORT", "")
    if port.isdigit():
        threading.Thread(target=start_keepalive, args=(int(port),), daemon=True).start()

    app = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .defaults(Defaults(parse_mode=ParseMode.HTML))
        .rate_limiter(AIORateLimiter())
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", handlers.cmd_start))
    app.add_handler(CommandHandler("help", handlers.cmd_help))
    app.add_handler(CommandHandler("stats", handlers.cmd_stats))
    app.add_handler(CommandHandler("users", handlers.cmd_users))
    app.add_handler(CommandHandler("broadcast", handlers.cmd_broadcast))
    app.add_handler(CommandHandler("update", handlers.cmd_update))
    app.add_handler(CallbackQueryHandler(handlers.on_quality, pattern=r"^dl\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_link))
    app.add_handler(MessageHandler(filters.Caption, handlers.handle_link))

    log.info("جاري تشغيل البوت... 🎬")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
