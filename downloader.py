"""محرك التحميل بواسطة yt-dlp — بيدعم يوتيوب وفيسبوك وانستجرام وتيك توك و X"""
import os
import re
import shutil
import tarfile
import threading
import urllib.request

import yt_dlp

import config
from utils import fmt_size

# حد أقصى للتحميلات المتزامنة
_SEM = threading.Semaphore(config.MAX_CONCURRENT)

# ─── تنزيل ffmpeg تلقائياً (للبيئات اللي ملهاش ffmpeg زي Vercel) ───
_FFMPEG_LOCK = threading.Lock()
_FFMPEG_READY = threading.Event()


def ensure_ffmpeg(timeout=30):
    """لو مفيش ffmpeg على النظام — بينزّل نسخة ثابتة في /tmp"""
    if _FFMPEG_READY.is_set() or shutil.which("ffmpeg"):
        _FFMPEG_READY.set()
        return True
    if not _FFMPEG_LOCK.acquire(timeout=timeout):
        return _FFMPEG_READY.is_set()
    try:
        if _FFMPEG_READY.is_set() or shutil.which("ffmpeg"):
            _FFMPEG_READY.set()
            return True
        target = os.getenv("FFMPEG_DIR") or "/tmp/ffmpeg"
        try:
            os.makedirs(target, exist_ok=True)
            ffmpeg_bin = os.path.join(target, "ffmpeg")
            if not (os.path.exists(ffmpeg_bin) and os.path.exists(os.path.join(target, "ffprobe"))):
                sources = [
                    "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
                    "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-linux64-gpl.tar.xz",
                ]
                archive = os.path.join(target, "ff.tar.xz")
                ok_download = False
                for src in sources:
                    try:
                        urllib.request.urlretrieve(src, archive)
                        ok_download = True
                        break
                    except Exception:
                        continue
                if not ok_download:
                    return False
                with tarfile.open(archive, "r:xz") as tf:
                    for member in tf.getmembers():
                        base = os.path.basename(member.name)
                        if base in ("ffmpeg", "ffprobe"):
                            member.name = base
                            tf.extract(member, target)
                for name in ("ffmpeg", "ffprobe"):
                    bin_path = os.path.join(target, name)
                    if os.path.exists(bin_path):
                        os.chmod(bin_path, 0o755)
                try:
                    os.remove(archive)
                except OSError:
                    pass
            if os.path.exists(ffmpeg_bin):
                os.environ["FFMPEG_DIR"] = target
                _FFMPEG_READY.set()
                return True
            return False
        except Exception:
            return False
    finally:
        _FFMPEG_LOCK.release()

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
AUDIO_EXTS = {"mp3", "m4a", "aac", "opus", "ogg", "wav"}
VIDEO_EXTS = {"mp4", "mkv", "webm", "mov", "avi", "flv", "m4v"}

PLATFORMS = [
    ("YouTube", "📺", ("youtube.com", "youtu.be")),
    ("Facebook", "👍", ("facebook.com", "fb.watch", "fb.com")),
    ("Instagram", "📸", ("instagram.com", "instagr.am")),
    ("TikTok", "🎵", ("tiktok.com",)),
    ("X (تويتر)", "🐦", ("twitter.com", "x.com")),
]


class Platform:
    def __init__(self, name, emoji):
        self.name = name
        self.emoji = emoji


def detect_platform(url):
    u = (url or "").lower()
    for name, emoji, domains in PLATFORMS:
        if any(d in u for d in domains):
            return Platform(name, emoji)
    m = re.search(r"(?:https?://)?(?:www\.)?([^/\s]+)", u)
    return Platform(m.group(1) if m else "لينك", "🌐")


def is_image(info):
    """هل العنصر ده صورة مش فيديو؟ (صور انستجرام وتيك توك)"""
    if not info:
        return False
    ext = str(info.get("ext") or "").lower()
    if ext in IMAGE_EXTS:
        return True
    if info.get("vcodec") == "none" and not info.get("duration"):
        return True
    return False


def _base_opts(outdir=None, playlist_mode=False, hook=None, post_hook=None):
    pattern = "%(playlist_index)02d - %(title).40s.%(ext)s" if playlist_mode else "%(title).60s.%(ext)s"
    opts = {
        "outtmpl": os.path.join(outdir or ".", pattern),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "overwrites": True,
        "noplaylist": not playlist_mode,
        "ignoreerrors": bool(playlist_mode),
        "windowsfilenames": True,
    }
    if playlist_mode:
        opts["playlist_items"] = "1:10"
    if hook:
        opts["progress_hooks"] = [hook]
    if post_hook:
        opts["postprocessor_hooks"] = [post_hook]
    if config.COOKIES_FILE and os.path.exists(config.COOKIES_FILE):
        opts["cookiefile"] = config.COOKIES_FILE
    ffmpeg_dir = os.getenv("FFMPEG_DIR")
    if ffmpeg_dir and os.path.exists(os.path.join(ffmpeg_dir, "ffmpeg")):
        opts["ffmpeg_location"] = ffmpeg_dir
    return opts


def extract_info_sync(url):
    """جيب معلومات الفيديو من غير تحميل (عنوان/مدة/جودات متاحة)"""
    opts = _base_opts()
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise RuntimeError("مقدرتش أقرا بيانات اللينك")
    return info


def _collect_file(outdir, kind):
    """يدوّر على الملف الناتج في فولدر التحميل"""
    files = []
    for root, _, names in os.walk(outdir):
        for n in names:
            if not n.startswith("."):
                files.append(os.path.join(root, n))
    if not files:
        return None
    if kind == "audio":
        pref = [f for f in files if f.rsplit(".", 1)[-1].lower() in AUDIO_EXTS]
        cand = pref or files
    elif kind == "video":
        pref = [f for f in files if f.rsplit(".", 1)[-1].lower() in VIDEO_EXTS]
        cand = pref or files
    else:
        cand = files
    return max(cand, key=os.path.getsize)


def _collect_all(outdir):
    files = []
    for root, _, names in os.walk(outdir):
        for n in names:
            if not n.startswith("."):
                files.append(os.path.join(root, n))
    return sorted(files)


def _finalize(info, path, kind):
    ext = path.rsplit(".", 1)[-1].lower() if "." in os.path.basename(path) else ""
    if ext in IMAGE_EXTS:
        kind = "image"
    d = info if isinstance(info, dict) else {}
    return {
        "path": path,
        "kind": kind,
        "title": d.get("title") or os.path.splitext(os.path.basename(path))[0],
        "duration": d.get("duration"),
        "width": d.get("width"),
        "height": d.get("height"),
        "thumbnail": d.get("thumbnail"),
    }


def _run_download(opts, url, outdir, kind):
    info = None
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        # لو ffmpeg مش موجود: جرب ملف واحد جاهز من غير دمج
        if "ffmpeg" in str(e).lower() and kind == "video":
            opts.pop("postprocessors", None)
            opts["format"] = "best[ext=mp4]/best"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        else:
            raise
    except yt_dlp.utils.PostProcessingError:
        # فشل تحويل MP3 (بدون ffmpeg مثلاً) — استخدم الصوت الخام زي m4a
        if kind == "audio":
            path = _collect_file(outdir, "audio")
            if path:
                return _finalize(info, path, kind)
        raise
    path = _collect_file(outdir, kind)
    if not path:
        raise RuntimeError("مقدرتش أنزّل الملف")
    return _finalize(info, path, kind)


def download_media_sync(url, quality, audio_only, outdir, hook=None, post_hook=None):
    """ينزّل فيديو/صوت/صورة واحدة — بيرجع dict فيه الملف وبياناته"""
    with _SEM:
        if not shutil.which("ffmpeg"):
            ensure_ffmpeg(timeout=25)
        opts = _base_opts(outdir, hook=hook, post_hook=post_hook)
        if audio_only:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
            kind = "audio"
        else:
            q = quality or "1080"
            opts["format"] = (
                f"bestvideo[height<={q}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={q}]+bestaudio/"
                f"best[height<={q}]/best"
            )
            opts["merge_output_format"] = "mp4"
            kind = "video"
        return _run_download(opts, url, outdir, kind)


def download_playlist_sync(url, outdir):
    """ينزّل كاروسيل (صور/ريلز انستجرام وتيك توك) — بيرجع قايمة الملفات"""
    with _SEM:
        if not shutil.which("ffmpeg"):
            ensure_ffmpeg(timeout=25)
        opts = _base_opts(outdir, playlist_mode=True)
        opts["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        opts["merge_output_format"] = "mp4"
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            if "ffmpeg" in str(e).lower():
                opts["format"] = "best/best"
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
            else:
                raise
        files = _collect_all(outdir)
        if not files:
            raise RuntimeError("مقدرتش أنزّل الملفات")
        return files


def _best_audio(fmts):
    best = None
    for f in fmts:
        if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none"):
            score = f.get("abr") or f.get("tbr") or 0
            if best is None or score > (best.get("abr") or best.get("tbr") or 0):
                best = f
    return best


def _est_text(fmt, info):
    if not fmt:
        return None
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if not size:
        tbr = fmt.get("tbr") or fmt.get("abr")
        dur = info.get("duration")
        if tbr and dur:
            size = tbr * 1000 / 8 * dur
    if size and size > 0:
        return f"~{fmt_size(size)}"
    return None


def estimate_size(info, quality):
    """تقدير حجم الملف قبل التحميل — بيرجع نص زي '~12MB' أو None لو مش قادر"""
    try:
        if not info:
            return None
        fmts = [f for f in (info.get("formats") or []) if isinstance(f, dict)]
        if quality == "audio":
            return _est_text(_best_audio(fmts), info)
        q = int(quality)
        best_v, best_h = None, 0
        for f in fmts:
            h = f.get("height")
            if not h or f.get("vcodec") in (None, "none"):
                continue
            if h <= q and h > best_h:
                best_v, best_h = f, h
        if not best_v:
            return None
        vsize = best_v.get("filesize") or best_v.get("filesize_approx")
        if not vsize:
            tbr, dur = best_v.get("tbr"), info.get("duration")
            if tbr and dur:
                vsize = tbr * 1000 / 8 * dur
        if not vsize:
            return None
        total = vsize
        a = _best_audio(fmts)
        if a:
            asize = a.get("filesize") or a.get("filesize_approx")
            if not asize:
                tbr, dur = a.get("tbr") or a.get("abr"), info.get("duration")
                if tbr and dur:
                    asize = tbr * 1000 / 8 * dur
            total += asize or 0
        return f"~{fmt_size(total)}"
    except Exception:
        return None
