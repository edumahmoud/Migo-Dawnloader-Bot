"""كل رسايل البوت بالعربي المصري في مكان واحد 🇪🇬✨"""
import html

import config
from utils import LINE, fmt_size

WELCOME = (
    "🎬 <b>أهلاً بيك في بوت تحميل الفيديوهات!</b> 🚀\n\n"
    f"{LINE}\n"
    "📥 <b>ابعتهولي لينك من أي منصة دول:</b>\n"
    "📺 يوتيوب • 👍 فيسبوك • 📸 انستجرام\n"
    "🎵 تيك توك • 🐦 X (تويتر)\n"
    f"{LINE}\n\n"
    "✨ ابعت <b>لينك الفيديو</b> بس..\n"
    "🎯 هظهرلك أزرار الجودات واختار اللي يناسبك وأنزّهالك فوراً\n\n"
    "💡 <i>اكتب /help لطريقة الاستخدام</i>"
)

HELP = (
    "📖 <b>دليل الاستخدام</b> 🧭\n\n"
    f"{LINE}\n"
    "🟦 <b>الخطوات:</b>\n"
    "1️⃣ هات لينك الفيديو من أي منصة مدعومة\n"
    "2️⃣ ابعت اللينك هنا في الشات\n"
    "3️⃣ اختار الجودة 🎬 أو صوت MP3 🎵\n"
    "4️⃣ استنى شوية والملف هيوصلك ✅\n"
    f"{LINE}\n"
    "🟩 <b>الأوامر:</b>\n"
    "▶️ /start — تشغيل البوت\n"
    "▶️ /help — عرض المساعدة دي\n"
    "▶️ /stats — إحصائيات التحميل\n"
    f"{LINE}\n"
    "🟨 <b>ملاحظات مهمة:</b>\n"
    "<blockquote>⚠️ أقصى حجم للملف 50MB (حسب قواعد تليجرام)\n"
    "🔒 المحتوى الخاص (حسابات خاصة) مش بيتحمّل\n"
    "🙌 استخدم البوت للاستخدام الشخصي بس</blockquote>"
)

HINT = (
    "🤔 <b>استنى!</b> ده مش لينك فيديو 😅\n\n"
    "📥 ابعتلي <b>لينك فيديو</b> وأنا هحمّلهولك فوراً\n"
    "مثال: <code>https://youtu.be/xxxx</code>"
)

CHECKING = "🔎 <b>جاري فحص اللينك...</b>\n⏳ استنى ثانية 👀"

SLOW = (
    "🐢 <b>العملية بياخد وقت أطول من المعتاد</b>\n\n"
    "⏳ جرب تاني بعد شوية، أو اتأكد إن اللينك شغال في المتصفح الأول."
)

EXPIRED = (
    "⌛ <b>انتهت صلاحية الاختيار</b>\n\n"
    "🔄 ابعت اللينك تاني واختار الجودة من أول وجديد"
)

NOT_YOURS = "😅 التحميل ده مش بتك!\n📥 ابعت لينكك انت واختار الجودة بنفسك."

BUSY = (
    "⏳ <b>عندك تحميل شغال دلوقتي!</b>\n\n"
    "☕ استنى يخلص الأول وبعدين ابعت لينك جديد"
)

UNSUPPORTED = (
    "🚫 <b>معرفتش أقرا اللينك ده</b>\n\n"
    "🌐 المنصات المدعومة:\n"
    "📺 يوتيوب • 👍 فيسبوك • 📸 انستجرام\n"
    "🎵 تيك توك • 🐦 X (تويتر)"
)


def rate_limited(sec):
    return (
        f"🐢 <b>هدوء شوية!</b> 🙏\n\n"
        f"⚡ بتبعت طلبات بسرعة كبيرة.\n"
        f"⏳ استنى <b>{sec}</b> ثانية وجرب تاني"
    )


def playlist_hint(n):
    return (
        "📋 <b>دي قايمة تشغيل (Playlist)</b>\n\n"
        f"🔢 فيها <b>{n}</b> فيديو — مش هقدر أنزلهم كلهم مرة واحدة.\n"
        "🎯 افتح الفيديو اللي عايزه وابعت <b>لينكه هو</b> بس 🙂"
    )


def too_big(size=None, limit=None):
    """رسالة تجاوز الحد — الحد بيتقرا من config.MAX_FILE_MB (ديناميكياً مش ثابت 50)"""
    lim = limit or config.MAX_FILE_MB
    size_line = f"📦 حجم الملف: <b>{size}</b>\n" if size else ""
    return (
        "🚫 <b>الملف أكبر من الحد المسموح!</b>\n\n"
        f"{size_line}"
        f"⚠️ تليجرام بيسمح للبوتات بحد أقصى <b>{lim}MB</b> للملف.\n\n"
        f"{LINE}\n"
        "🟩 <b>الحلول:</b>\n"
        "1️⃣ جرب جودة أقل (720p أو 480p)\n"
        "2️⃣ أو حمّله صوت MP3 بس 🎵"
    )


STAGE_PROCESS = "⚙️ <b>جاري المعالجة والدمج...</b>\n🛠 لحظات وتخلص"
STAGE_UPLOAD = "⬆️ <b>جاري الرفع على تليجرام...</b>\n✈️ الملف في الطريق إليك"


def progress(pct, done, total):
    """شريط تقدم حي ملون: ⬇️ 45% 🟩🟩🟩🟩🟩⬜⬜⬜⬜⬜"""
    filled = int(round(pct / 100 * 10))
    filled = max(0, min(10, filled))
    bar = "🟩" * filled + "⬜" * (10 - filled)
    line = f"⬇️ <b>جاري التحميل</b> {pct:.0f}% ⚡\n{bar}\n"
    if total:
        line += f"📦 {fmt_size(done)} من {fmt_size(total)}"
    else:
        line += f"📦 {fmt_size(done)}"
    return line


def item_progress(i, n):
    return f"📥 <b>جاري تحميل العنصر {i} من {n}...</b>\n⏳ استنى شوية 🙌"


def done(title, size, elapsed, personal=None):
    """رسالة النجاح — personal = تحميلات المستخدم رقم كام (اختياري)"""
    t = html.escape(str(title or "الملف")[:80])
    extra = f"\n🏅 <b>ده تحميلك رقم {personal} معانا!</b>" if personal else ""
    return (
        "🎉 <b>تم التحميل والرفع بنجاح!</b> 🎊\n\n"
        f"{LINE}\n"
        f"🎬 {t}\n"
        f"📦 الحجم: {size}\n"
        f"⏱ استغرق: {elapsed} ثانية"
        f"{extra}\n"
        f"{LINE}\n"
        "💚 شكراً لاستخدامك البوت!"
    )


def result_caption(title, platform, size, bot_username):
    """كابشن الملف المرسل — عنوان + منصة + حجم + توقيع البوت"""
    t = html.escape(str(title or "")[:90])
    credit = f"\n\n🤖 @{bot_username}" if bot_username else ""
    return (
        f"✅ <b>{t}</b>\n"
        f"{LINE}\n"
        f"📡 {platform} • 📦 {size}{credit}"
    )


def stats_line(total, users=None, personal=None):
    """سطر إحصائيات سريع بيظهر في بطاقة الفيديو"""
    parts = [f"⬇️ <b>{total}</b> تحميل"]
    if users is not None:
        parts.append(f"👥 <b>{users}</b> مستخدم")
    if personal is not None:
        parts.append(f"🔥 تحميلاتك <b>{personal}</b>")
    return "📊 " + " • ".join(parts)


PRIVATE_ERR = (
    "🔒 <b>المحتوى ده خاص!</b>\n\n"
    "الفيديو أو الحساب خاص ومش هيقدر يتحمّل.\n"
    "🌍 جرب فيديو عام تاني"
)

LOGIN_ERR = (
    "🔐 <b>المحتوى ده محتاج تسجيل دخول</b>\n\n"
    "لو انستجرام أو فيسبوك خاص — صاحب البوت لازم يضيف ملف كوكيز.\n"
    "🙂 جرب لينك تاني عام"
)

GONE_ERR = (
    "🗑 <b>المحتوى ده مش متاح</b>\n\n"
    "يمكن اتحذف أو اتعمل له خصوصي.\n"
    "🔄 جرب لينك تاني"
)

FFMPEG_ERR = (
    "⚙️ <b>ffmpeg مش متسطّب على السيرفر!</b>\n\n"
    "ده محتاج من صاحب البوت إنه يسطبه:\n"
    "<code>apt install ffmpeg</code>"
)


def error_for(e):
    """ترجمة أخطاء yt-dlp وتليجرام لرسايل مفهومة"""
    s = str(e).lower()
    # تليجرام نفسه رفض الرفع (413) — لو الملف عدّى الفحص واترفض وقت الرفع
    if "entity too large" in s or "file is too big" in s or "payload too large" in s:
        return too_big()
    if "private" in s:
        return PRIVATE_ERR
    if "login" in s or "cookies" in s or "sign in" in s or "authentication" in s or "confirm you" in s:
        return LOGIN_ERR
    if "unsupported url" in s or "no video could be found" in s or "unable to extract" in s:
        return UNSUPPORTED
    if "unavailable" in s or "removed" in s or "not exist" in s or "404" in s:
        return GONE_ERR
    if "ffmpeg" in s:
        return FFMPEG_ERR
    msg = html.escape(str(e)[:180])
    return (
        "😵 <b>حصلت مشكلة غير متوقعة!</b>\n\n"
        f"💥 <code>{msg}</code>\n\n"
        "🙏 جرب تاني أو ابعت لينك تاني"
    )
