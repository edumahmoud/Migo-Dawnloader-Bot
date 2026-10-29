"""معالجات رسايل وأزرار البوت"""
import asyncio
import functools
import html
import logging
import os
import re
import shutil
import time
import uuid

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import ContextTypes

import config
import strings
from antispam import limiter
from downloader import (IMAGE_EXTS, detect_platform, download_media_sync,
                        download_playlist_sync, estimate_size, extract_info_sync, is_image)
from sender import send_audio_file, send_photo_file, send_video_file
from stats import stats
from utils import LINE, fmt_duration, fmt_size

log = logging.getLogger("handlers")

PENDING = {}       # req_id -> بيانات الاختيار المعلق
PENDING_TTL = 900  # 15 دقيقة
ACTIVE = set()     # مستخدمين عندهم تحميل شغال حالياً
BOT_USERNAME = ""  # بيتحدد تلقائياً عند التشغيل

URL_RE = re.compile(r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+)", re.I)

BOT_COMMANDS = [
    BotCommand("start", "تشغيل البوت"),
    BotCommand("help", "طريقة الاستخدام"),
    BotCommand("stats", "إحصائيات التحميل"),
]


def _is_admin(user_id):
    return user_id in config.ADMIN_IDS


async def _progress_edit(msg, text):
    """تعديل رسالة الحالة بأمان (نص عادي أو صورة بكابشن) — ولو الHTML اترفض نرجع للنص العادي"""
    try:
        return await msg.edit_text(text, disable_web_page_preview=True)
    except BadRequest as e:
        s = str(e).lower()
        if "can't parse entities" in s:
            try:
                return await msg.edit_text(text, parse_mode=None)
            except TelegramError:
                return msg
        if "no text" in s:
            try:
                return await msg.edit_caption(caption=text)
            except BadRequest as e2:
                if "can't parse entities" in str(e2).lower():
                    try:
                        return await msg.edit_caption(caption=text, parse_mode=None)
                    except TelegramError:
                        return msg
                return msg
            except TelegramError:
                return msg
        return msg
    except TelegramError:
        return msg


# ─────────────────────── الأوامر الأساسية ───────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(strings.WELCOME, disable_web_page_preview=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(strings.HELP, disable_web_page_preview=True)


# ─────────────────────── استقبال اللينكات ───────────────────────

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user:
        return
    text = msg.text or msg.caption or ""
    m = URL_RE.search(text)
    if not m:
        if update.effective_chat.type == "private":
            await msg.reply_text(strings.HINT)
        return

    # تنظيف الطلبات القديمة المنتهية
    now = time.time()
    for k in [k for k, v in PENDING.items() if v["ttl"] < now]:
        PENDING.pop(k, None)

    allowed, retry = limiter.check(user.id)
    if not allowed:
        await msg.reply_text(strings.rate_limited(retry))
        return
    if user.id in ACTIVE:
        await msg.reply_text(strings.BUSY)
        return

    url = m.group(1)
    status = await msg.reply_text(strings.CHECKING)

    loop = asyncio.get_running_loop()
    try:
        info = await asyncio.wait_for(
            loop.run_in_executor(None, functools.partial(extract_info_sync, url)),
            timeout=90,
        )
    except asyncio.TimeoutError:
        await _progress_edit(status, strings.SLOW)
        return
    except Exception as e:
        log.warning("extract failed for %s: %s", url, e)
        await _progress_edit(status, strings.error_for(e))
        return

    # قوائم التشغيل والكاروسيل (صور انستجرام/تيك توك)
    entries = []
    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]

    if entries:
        videos = [e for e in entries if not is_image(e)]
        images = [e for e in entries if is_image(e)]
        if len(videos) > 1:
            await _progress_edit(status, strings.playlist_hint(len(videos)))
            return
        if videos:
            # فيديو واحد جوه القايمة (زي تيك توك) — نعامله عادي
            info = videos[0]
        elif images:
            await _run_carousel(status, info.get("webpage_url") or url, user, len(images))
            return

    await _show_quality_menu(status, url, info, user)


async def _show_quality_menu(status, url, info, user):
    """عرض بطاقة الفيديو + أزرار الجودات"""
    req_id = uuid.uuid4().hex[:10]
    PENDING[req_id] = {
        "url": info.get("webpage_url") or url,
        "user_id": user.id,
        "ttl": time.time() + PENDING_TTL,
    }

    platform = detect_platform(info.get("webpage_url") or url)
    title = html.escape(str(info.get("title") or "فيديو")[:120])
    dur = fmt_duration(info.get("duration"))
    uploader = html.escape(str(info.get("uploader") or "")[:60])

    link = html.escape(str(info.get("webpage_url") or url))
    cap = f"{platform.emoji} <b>{platform.name}</b>\n{LINE}\n🎬 <b>{title}</b>"
    if dur and dur != "—":
        cap += f"\n⏱ المدة: {dur}"
    if uploader:
        cap += f"\n👤 {uploader}"
    # اللينك في الرسالة عشان نقدر نسترجعه لو السيرفر أعاد التشغيل (زي على Vercel)
    cap += f"\n🔗 <code>{link}</code>\n{LINE}"
    # إحصائيات سريعة في بطاقة الفيديو — كاملة للأدمن، وسطر بسيط لغيره
    if _is_admin(user.id):
        cap += "\n" + strings.stats_line(
            stats.total_count(), stats.user_count(), stats.user_downloads(user.id)
        )
    else:
        cap += "\n" + strings.stats_line(stats.total_count())
    cap += f"\n{LINE}\n\n👇 <b>اختار الجودة اللي تحبها:</b>"

    def btn(label, quality):
        est = estimate_size(info, quality)
        extra = f" • {est}" if est else ""
        return InlineKeyboardButton(f"{label}{extra}", callback_data=f"dl|{req_id}|{quality}")

    # ألوان الجودات: 🟢 الأعلى → 🟡 متوسطة → 🟠 الاقتصادية
    markup = InlineKeyboardMarkup([
        [btn("🟢 1080p", "1080"), btn("🟡 720p", "720")],
        [btn("🟠 480p", "480"), btn("🎧 صوت MP3", "audio")],
    ])

    thumb = info.get("thumbnail")
    if thumb:
        try:
            await status.delete()
            await status.chat.send_photo(photo=thumb, caption=cap, reply_markup=markup)
            return
        except TelegramError:
            pass
    await _progress_edit(status, cap)
    try:
        await status.edit_reply_markup(reply_markup=markup)
    except TelegramError:
        pass


# ─────────────────────── اختيار الجودة والتحميل ───────────────────────

async def on_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data or ""
    try:
        _, req_id, quality = data.split("|", 2)
    except ValueError:
        await q.answer()
        return

    msg = q.message
    job = PENDING.get(req_id)
    if not job:
        # لو السيرفر أعاد التشغيل (زي على Vercel) — نسترجع اللينك من الرسالة نفسها
        menu_text = (getattr(msg, "caption", None) or getattr(msg, "text", None) or "")
        recovered = URL_RE.search(menu_text)
        if not recovered:
            await q.answer()
            await _progress_edit(msg, strings.EXPIRED)
            return
        job = {"url": recovered.group(1), "user_id": q.from_user.id, "ttl": time.time() + PENDING_TTL}
        PENDING[req_id] = job
    if q.from_user.id != job["user_id"]:
        await q.answer(strings.NOT_YOURS, show_alert=True)
        return
    if time.time() > job["ttl"]:
        PENDING.pop(req_id, None)
        await q.answer()
        await _progress_edit(msg, strings.EXPIRED)
        return

    user = q.from_user
    allowed, retry = limiter.check(user.id)
    if not allowed:
        await q.answer(strings.rate_limited(retry), show_alert=True)
        return
    if user.id in ACTIVE:
        await q.answer(strings.BUSY, show_alert=True)
        return

    await q.answer()
    PENDING.pop(req_id, None)
    ACTIVE.add(user.id)

    url = job["url"]
    audio_only = quality == "audio"
    loop = asyncio.get_running_loop()
    start = time.time()
    outdir = os.path.join(config.DOWNLOAD_DIR, uuid.uuid4().hex)
    os.makedirs(outdir, exist_ok=True)

    last_edit = {"t": 0.0}

    def hook(d):
        # شريط التقدم — بيتحدث كل ثانيتين بس عشان ما نزنقش تليجرام
        if d.get("status") == "finished":
            return
        now = time.time()
        if now - last_edit["t"] < 2.0:
            return
        last_edit["t"] = now
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        done = d.get("downloaded_bytes") or 0
        pct = (done / total * 100) if total else 0
        text = strings.progress(pct, done, total)
        asyncio.run_coroutine_threadsafe(_progress_edit(msg, text), loop)

    def post_hook(d):
        if d.get("status") == "started":
            asyncio.run_coroutine_threadsafe(_progress_edit(msg, strings.STAGE_PROCESS), loop)

    try:
        await _progress_edit(msg, strings.progress(0, 0, 0))
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                functools.partial(
                    download_media_sync,
                    url=url,
                    quality=None if audio_only else quality,
                    audio_only=audio_only,
                    outdir=outdir,
                    hook=hook,
                    post_hook=post_hook,
                ),
            ),
            timeout=1800,
        )

        path = result["path"]
        size = os.path.getsize(path)
        if size > config.MAX_FILE_MB * 1024 * 1024:
            await _progress_edit(msg, strings.too_big(fmt_size(size)))
            return

        platform = detect_platform(url)
        await _progress_edit(msg, strings.STAGE_UPLOAD)
        caption = strings.result_caption(
            result.get("title") or "",
            f"{platform.emoji} {platform.name}",
            fmt_size(size),
            BOT_USERNAME,
        )

        if result["kind"] == "audio":
            await send_audio_file(msg, path, result, caption, thumb_url=result.get("thumbnail"))
        elif result["kind"] == "image":
            await send_photo_file(msg, path, caption)
        else:
            await send_video_file(msg, path, result, caption, thumb_url=result.get("thumbnail"))

        stats.record(user.id, user.first_name or "", platform.name)
        await stats.maybe_sync(context.bot)  # نسخة احتياطية للإحصائيات في قناة التخزين
        elapsed = max(1, int(time.time() - start))
        # العدد شامل التحميل ده لأن record اتعملت لسه — عشان يظهر "ده تحميلك رقم كام"
        personal = stats.user_downloads(user.id)
        await _progress_edit(
            msg,
            strings.done(result.get("title") or "", fmt_size(size), elapsed, personal=personal),
        )

    except asyncio.TimeoutError:
        await _progress_edit(msg, strings.SLOW)
    except Exception as e:
        log.exception("download failed: %s", url)
        await _progress_edit(msg, strings.error_for(e))
    finally:
        ACTIVE.discard(user.id)
        shutil.rmtree(outdir, ignore_errors=True)


# ─────────────────────── الكاروسيل (صور متعددة) ───────────────────────

async def _run_carousel(status, url, user, count):
    loop = asyncio.get_running_loop()
    outdir = os.path.join(config.DOWNLOAD_DIR, uuid.uuid4().hex)
    os.makedirs(outdir, exist_ok=True)
    ACTIVE.add(user.id)
    n = min(count, 10)
    try:
        await _progress_edit(status, strings.item_progress(1, n))
        files = await asyncio.wait_for(
            loop.run_in_executor(None, functools.partial(download_playlist_sync, url, outdir)),
            timeout=1800,
        )
        files = files[:10]
        if not files:
            await _progress_edit(status, strings.UNSUPPORTED)
            return

        photos, others = [], []
        for f in files:
            ext = f.rsplit(".", 1)[-1].lower()
            if ext in IMAGE_EXTS:
                photos.append(f)
            else:
                others.append(f)

        sent = 0
        if photos:
            await _progress_edit(status, "⬆️ <b>جاري رفع الصور...</b>")
            media = []
            for p in photos:
                try:
                    with open(p, "rb") as fh:
                        media.append(InputMediaPhoto(media=fh.read()))
                except OSError:
                    continue
            if len(media) == 1:
                await status.reply_photo(photo=media[0].media)
                sent += 1
            else:
                for chunk in [media[i:i + 10] for i in range(0, len(media), 10)]:
                    await status.reply_media_group(media=chunk)
                    sent += len(chunk)

        platform = detect_platform(url)
        for v in others[:3]:
            try:
                size = os.path.getsize(v)
            except OSError:
                continue
            if size > config.MAX_FILE_MB * 1024 * 1024:
                continue
            await _progress_edit(status, strings.STAGE_UPLOAD)
            caption = strings.result_caption(
                "عنصر من الكاروسيل", f"{platform.emoji} {platform.name}",
                fmt_size(size), BOT_USERNAME,
            )
            await send_video_file(status, v, {}, caption)
            sent += 1

        stats.record(user.id, user.first_name or "", platform.name)
        await stats.maybe_sync(status.get_bot())  # نسخة احتياطية للإحصائيات
        await _progress_edit(status, f"🎉 <b>خلصنا!</b> اتبعت <b>{sent}</b> ملف جاهزين 🎊")

    except asyncio.TimeoutError:
        await _progress_edit(status, strings.SLOW)
    except Exception as e:
        log.exception("carousel failed: %s", url)
        await _progress_edit(status, strings.error_for(e))
    finally:
        ACTIVE.discard(user.id)
        shutil.rmtree(outdir, ignore_errors=True)


# ─────────────────────── الإحصائيات وأوامر الأدمن ───────────────────────

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    full = _is_admin(user.id)
    text = stats.summary_text(full=full, bot_username=BOT_USERNAME)
    await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.effective_message.reply_text("🚫 <b>الأمر ده للأدمن بس!</b>")
        return
    text = stats.summary_text(full=True, bot_username=BOT_USERNAME)
    await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.effective_message.reply_text("🚫 <b>الأمر ده للأدمن بس!</b>")
        return
    text = " ".join(context.args or []).strip()
    if not text:
        await update.effective_message.reply_text(
            "✍️ اكتب الرسالة بعد الأمر:\n<code>/broadcast أهلاً بالجميع 👋</code>"
        )
        return
    ids = stats.user_ids()
    if not ids:
        await update.effective_message.reply_text("😔 مفيش مستخدمين مسجلين لسه.")
        return
    status = await update.effective_message.reply_text(f"📤 <b>جاري الإرسال لـ {len(ids)} مستخدم...</b> ⏳")
    ok = fail = 0
    for uid in ids:
        try:
            try:
                await context.bot.send_message(uid, text)
            except BadRequest as e:
                # لو الأدمن كتب حرف زي < في نص الإذاعي — نبعته من غير تنسيق بدل ما يفشل
                if "can't parse entities" in str(e).lower():
                    await context.bot.send_message(uid, text, parse_mode=None)
                else:
                    raise
            ok += 1
        except TelegramError:
            fail += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"📤 <b>خلص الإرسال!</b> 🎯\n✅ وصلت لـ {ok}\n❌ فشلت لـ {fail}")


async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.effective_message.reply_text("🚫 <b>الأمر ده للأدمن بس!</b>")
        return
    msg = await update.effective_message.reply_text("⏳ <b>جاري تحديث yt-dlp...</b> استنى شوية")

    def _upd():
        import yt_dlp.update
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            yt_dlp.update.selfupdate(ydl)

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _upd)
        await msg.edit_text("✅ <b>اتحدث yt-dlp لآخر نسخة!</b>\n♻️ أعد تشغيل البوت عشان التغيير يشتغل.")
    except SystemExit:
        await msg.edit_text("✅ <b>اتحدث yt-dlp!</b>\n♻️ أعد تشغيل البوت.")
    except Exception as e:
        await msg.edit_text(
            "❌ <b>معرفش يحدث تلقائياً.</b>\n"
            "حدث يدوياً بالأمر:\n<code>pip install -U yt-dlp</code>\n\n"
            f"<code>{html.escape(str(e)[:120])}</code>"
        )
