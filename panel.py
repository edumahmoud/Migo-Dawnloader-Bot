"""لوحة إحصائيات ويب — صفحة عربية (RTL) بتصميم داكن بتعرض حالة البوت

بتتعرض على / أو /stats — محمية بمفتاح (PANEL_KEY أو توكن البوت).
الصفحة بتترندر من السيرفر مباشرة (من غير JavaScript للبيانات) وتتحدث لوحدها كل دقيقة.
"""
import datetime
import html as _h
import time

from utils import fmt_size  # noqa: F401 (متاحة للاستخدام المستقبلي)

MEDALS = ("🥇", "🥈", "🥉")
DAY_NAMES = ["اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت", "أحد"]  # weekday() 0=اثنين

_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:radial-gradient(1100px 500px at 85% -10%,#164e63aa,transparent),
     radial-gradient(900px 500px at -10% 110%,#065f4633,transparent),#0b1220;
     color:#e8eefc;font-family:Cairo,'Segoe UI',Tahoma,sans-serif;padding:28px 16px;min-height:100vh}
.wrap{max-width:980px;margin:0 auto}
h1{font-size:26px;font-weight:900;display:flex;align-items:center;gap:10px}
h1 .logo{font-size:30px}
.sub{color:#8ea0c0;font-size:13.5px;margin:8px 0 24px}
.badge{display:inline-block;background:#ffffff12;border:1px solid #ffffff1f;border-radius:99px;
       padding:3px 12px;font-size:12px;margin-inline-end:6px}
.badge.ok{color:#6ee7b7;border-color:#6ee7b755}
.badge.warn{color:#fbbf24;border-color:#fbbf2455}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:22px}
.card{background:linear-gradient(165deg,#141e33,#101a2d);border:1px solid #ffffff14;
      border-radius:18px;padding:20px;box-shadow:0 8px 24px #00000040}
.kpi .v{font-size:36px;font-weight:900;color:#34d399;line-height:1.2}
.kpi.b .v{color:#38bdf8}.kpi.p .v{color:#a78bfa}.kpi.o .v{color:#fbbf24}
.kpi .t{color:#8ea0c0;font-size:14px;margin-top:4px;font-weight:700}
.sect{font-size:17px;font-weight:900;margin:26px 0 12px;display:flex;align-items:center;gap:8px}
.row{display:flex;align-items:center;gap:12px;margin:10px 0}
.row .pl{width:150px;font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .bar{flex:1;height:14px;background:#ffffff0d;border-radius:99px;overflow:hidden}
.row .bar i{display:block;height:100%;border-radius:99px;
            background:linear-gradient(90deg,#34d399,#38bdf8)}
.row b{width:64px;text-align:left;font-size:14px;color:#cde3ff}
.week{display:flex;gap:10px;align-items:flex-end;height:150px;padding:8px 4px 0}
.day{flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;height:100%;justify-content:flex-end}
.day .c{font-size:12px;color:#8ea0c0;font-weight:700}
.day i{display:block;width:100%;max-width:44px;border-radius:8px 8px 3px 3px;
       background:linear-gradient(180deg,#38bdf8,#34d399);min-height:5px}
.day .n{font-size:11px;color:#8ea0c0}
.users{list-style:none}
.users li{display:flex;align-items:center;gap:10px;padding:9px 4px;border-bottom:1px solid #ffffff0a;font-size:14.5px}
.users li:last-child{border-bottom:none}
.users .rank{width:30px;text-align:center}
.users .nm{flex:1;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.users .ct{color:#6ee7b7;font-weight:900}
.note{background:#7c2d1233;border:1px solid #fbbf2444;border-radius:12px;padding:12px 14px;
      font-size:13.5px;color:#fde68a;margin-top:22px;line-height:1.9}
.footer{color:#8ea0c0;font-size:12.5px;text-align:center;margin-top:26px;line-height:2}
/* صفحة الدخول */
.login{max-width:420px;margin:12vh auto 0;text-align:center}
.login .card{padding:34px 26px}
.login h2{font-size:21px;margin-bottom:8px}
.login p{color:#8ea0c0;font-size:13.5px;margin-bottom:20px;line-height:1.9}
.login input{width:100%;background:#0b1220;border:1px solid #ffffff22;color:#e8eefc;border-radius:12px;
             padding:13px 14px;font-size:15px;font-family:inherit;direction:ltr;text-align:center}
.login button{width:100%;margin-top:14px;background:linear-gradient(90deg,#10b981,#38bdf8);border:none;
              color:#04121c;font-weight:900;font-size:16px;font-family:inherit;border-radius:12px;
              padding:13px;cursor:pointer}
.login button:hover{filter:brightness(1.1)}
"""


def _esc(s):
    return _h.escape(str(s))


def _login_page():
    """صفحة طلب المفتاح — من غير أي بيانات"""
    return (
        "<!doctype html><html dir=\"rtl\" lang=\"ar\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>🔐 لوحة إحصائيات البوت</title>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap\" rel=\"stylesheet\">"
        f"<style>{_CSS}</style></head><body>"
        "<div class=\"login\"><div class=\"card\">"
        "<h2>🔐 <b>لوحة إحصائيات البوت</b></h2>"
        "<p>الصفحة دي محمية — اكتب مفتاح الدخول عشان تشوف الإحصائيات<br>"
        "(المفتاح هو <b>PANEL_KEY</b> أو توكن البوت)</p>"
        "<form onsubmit=\"location='/stats?key='+encodeURIComponent(document.getElementById('k').value);return false\">"
        "<input id=\"k\" type=\"password\" placeholder=\"اكتب المفتاح هنا\" autocomplete=\"off\">"
        "<button type=\"submit\">🚪 دخول</button>"
        "</form></div></div></body></html>"
    )


def _platform_rows(platforms, total):
    """صفوف المنصات بأشرطة نسبية"""
    if not platforms:
        return "<p style=\"color:#8ea0c0;font-size:14px\">لسه مفيش تحميلات مسجلة 🌱</p>"
    ranked = sorted(platforms.items(), key=lambda x: -x[1])
    mx = max(1, max(c for _, c in ranked))
    out = []
    for name, cnt in ranked:
        w = int(cnt / mx * 100)
        out.append(
            f"<div class=\"row\"><span class=\"pl\">{_esc(name)}</span>"
            f"<div class=\"bar\"><i style=\"width:{w}%\"></i></div><b>{cnt}</b></div>"
        )
    return "".join(out)


def _week_chart(days):
    """رسم أعمدة لآخر 7 أيام"""
    today = datetime.date.today()
    counts = []
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        counts.append((d, int(days.get(d.isoformat(), 0))))
    mx = max(1, max(c for _, c in counts))
    out = []
    for d, c in counts:
        h = int(c / mx * 100)
        out.append(
            f"<div class=\"day\"><span class=\"c\">{c if c else ''}</span>"
            f"<i style=\"height:{max(5, h)}%\"></i>"
            f"<span class=\"n\">{DAY_NAMES[d.weekday()]}</span></div>"
        )
    return "".join(out)


def _top_users(users):
    if not users:
        return "<p style=\"color:#8ea0c0;font-size:14px\">لسه مفيش مستخدمين 🌱</p>"
    top = sorted(users.items(), key=lambda kv: -kv[1].get("count", 0))[:10]
    rows = []
    for i, (_, u) in enumerate(top, 1):
        rank = MEDALS[i - 1] if i <= 3 else f"{i}."
        rows.append(
            f"<li><span class=\"rank\">{rank}</span>"
            f"<span class=\"nm\">{_esc(u.get('name') or 'مستخدم')}</span>"
            f"<span class=\"ct\">{int(u.get('count', 0))} 📥</span></li>"
        )
    return "<ul class=\"users\">" + "".join(rows) + "</ul>"


def render_panel(stats_obj, bot_username="", storage_on=False, authorized=False):
    """يبنى صفحة اللوحة كاملة — لو authorized=False يرجّع صفحة المفتاح بس"""
    if not authorized:
        return _login_page()

    data = stats_obj.snapshot()
    total = int(data.get("total") or 0)
    users = data.get("users") or {}
    platforms = data.get("platforms") or {}
    days = data.get("days") or {}
    n_users = len(users)
    today = int(days.get(datetime.date.today().isoformat(), 0))
    avg = (total / n_users) if n_users else 0.0

    storage_badge = (
        "<span class=\"badge ok\">☁️ تخزين دائم مفعّل</span>"
        if storage_on else
        "<span class=\"badge warn\">⚠️ مفيش تخزين دائم</span>"
    )
    storage_note = "" if storage_on else (
        "<div class=\"note\">💡 <b>نصيحة:</b> الأرقام هنا محفوظة مؤقتاً وبتتصفر مع إعادة تشغيل السيرفر. "
        "عشان تخليها دائمة: أنشئ قناة خاصة في تليجرام، ضيف البوت أدمن فيها، "
        "وحط آيدي القناة في متغير <b>STATS_CHAT_ID</b> على Vercel.</div>"
    )

    bot_line = f"🤖 <b>@{_esc(bot_username)}</b>" if bot_username else "🤖 Migo Downloader"
    now_str = time.strftime("%Y-%m-%d %H:%M")

    return (
        "<!doctype html><html dir=\"rtl\" lang=\"ar\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<meta http-equiv=\"refresh\" content=\"60\">"
        "<title>📊 إحصائيات Migo Downloader</title>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap\" rel=\"stylesheet\">"
        f"<style>{_CSS}</style></head><body><div class=\"wrap\">"
        "<h1><span class=\"logo\">🤖</span> لوحة إحصائيات البوت</h1>"
        f"<div class=\"sub\">{bot_line} • {storage_badge} <span class=\"badge\">🕐 {now_str}</span></div>"

        "<div class=\"grid\">"
        f"<div class=\"card kpi\"><div class=\"v\">{total}</div><div class=\"t\">⬇️ إجمالي التحميلات</div></div>"
        f"<div class=\"card kpi b\"><div class=\"v\">{n_users}</div><div class=\"t\">👥 المستخدمين</div></div>"
        f"<div class=\"card kpi p\"><div class=\"v\">{today}</div><div class=\"t\">🔥 تحميلات النهارده</div></div>"
        f"<div class=\"card kpi o\"><div class=\"v\">{avg:.1f}</div><div class=\"t\">📈 متوسط لكل مستخدم</div></div>"
        "</div>"

        "<div class=\"card\">"
        "<div class=\"sect\">🌐 التحميلات حسب المنصة</div>"
        + _platform_rows(platforms, total) +
        "<div class=\"sect\">📅 آخر 7 أيام</div>"
        "<div class=\"week\">" + _week_chart(days) + "</div>"
        "<div class=\"sect\">🏆 أكثر المستخدمين نشاطاً</div>"
        + _top_users(users) +
        "</div>"

        + storage_note +
        f"<div class=\"footer\">Migo Downloader Bot • الصفحة بتتحدث تلقائياً كل 60 ثانية 🔄</div>"
        "</div></body></html>"
    )
