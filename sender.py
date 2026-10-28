"""إرسال الملفات المحمّلة على تليجرام (فيديو/صوت/صور)"""
import logging
import os

from telegram.error import TelegramError

log = logging.getLogger("sender")

PHOTO_LIMIT = 10 * 1024 * 1024  # حد الصور في تليجرام
BIG_TIMEOUTS = dict(write_timeout=900, read_timeout=900, pool_timeout=900, connect_timeout=120)


async def _fetch_thumb(url):
    """جلب صورة مصغرة للفيديو/الصوت (تليجرام بيقبلا أقل من 200KB)"""
    if not url:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code == 200 and 0 < len(r.content) <= 190_000:
                return r.content
    except Exception:
        pass
    return None


async def send_video_file(msg, path, info, caption, thumb_url=None):
    with open(path, "rb") as f:
        data = f.read()
    kwargs = dict(video=data, caption=caption, supports_streaming=True, **BIG_TIMEOUTS)
    if info:
        if info.get("duration"):
            kwargs["duration"] = int(info["duration"])
        if info.get("width"):
            kwargs["width"] = int(info["width"])
        if info.get("height"):
            kwargs["height"] = int(info["height"])
    thumb = await _fetch_thumb(thumb_url)
    if thumb:
        kwargs["thumbnail"] = thumb
    try:
        return await msg.reply_video(**kwargs)
    except TelegramError as e:
        log.warning("reply_video failed (%s) — جرّب تاني بأقل إعدادات", e)
        for k in ("duration", "width", "height", "thumbnail"):
            kwargs.pop(k, None)
        try:
            return await msg.reply_video(**kwargs)
        except TelegramError:
            # آخر حل: ابعت الملف كدوكيومنت
            return await msg.reply_document(document=data, caption=caption, **BIG_TIMEOUTS)


async def send_audio_file(msg, path, info, caption, thumb_url=None):
    with open(path, "rb") as f:
        data = f.read()
    kwargs = dict(audio=data, caption=caption, title=str(info.get("title") or "صوت")[:60], **BIG_TIMEOUTS)
    if info.get("duration"):
        kwargs["duration"] = int(info["duration"])
    if info.get("uploader"):
        kwargs["performer"] = str(info["uploader"])[:60]
    thumb = await _fetch_thumb(thumb_url)
    if thumb:
        kwargs["thumbnail"] = thumb
    try:
        return await msg.reply_audio(**kwargs)
    except TelegramError:
        for k in ("duration", "performer", "thumbnail", "title"):
            kwargs.pop(k, None)
        try:
            return await msg.reply_audio(**kwargs)
        except TelegramError:
            return await msg.reply_document(document=data, caption=caption, **BIG_TIMEOUTS)


async def send_photo_file(msg, path, caption):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) <= PHOTO_LIMIT:
        try:
            return await msg.reply_photo(photo=data, caption=caption)
        except TelegramError:
            pass
    return await msg.reply_document(
        document=data, filename=os.path.basename(path), caption=caption, **BIG_TIMEOUTS
    )
