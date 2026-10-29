"""لوحة إحصائيات ويب — صفحة عربية (RTL) بتصميم داكن + رسوم بيانية (Chart.js)

بتتعرض على / أو /stats — محمية بمفتاح (PANEL_KEY أو توكن البوت).
- كروت إحصائيات: الإجمالي • المستخدمين • النهارده • الأسبوع (٧ أيام) • الشهر • المتوسط
- رسم خطي لآخر 30 يوم + رسم دائري (دونات) لتوزيع المنصات + أشرطة تفصيلية
- جدول كامل لكل مستخدم: الاسم • اليوزرنيم • الآيدي • عدد التحميلات • تاريخ الاشتراك • آخر نشاط
الصفحة بتترندر من السيرفر مباشرة وبتتحدث لوحدها كل دقيقة.
"""
import datetime
import html as _h
import json as _json
import time

MEDALS = ("🥇", "🥈", "🥉")
DAY_NAMES = ["اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت", "أحد"]  # weekday() 0=اثنين
USERS_LIMIT = 200  # أقصى عدد صفوف في جدول المستخدمين (عشان الصفحة متتقلش)

_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:radial-gradient(1100px 500px at 85% -10%,#164e63aa,transparent),
     radial-gradient(900px 500px at -10% 110%,#065f4633,transparent),#0b1220;
     color:#e8eefc;font-family:Cairo,'Segoe UI',Tahoma,sans-serif;padding:28px 16px;min-height:100vh}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:26px;font-weight:900;display:flex;align-items:center;gap:10px}
h1 .logo{font-size:30px}
.sub{color:#8ea0c0;font-size:13.5px;margin:8px 0 24px}
.badge{display:inline-block;background:#ffffff12;border:1px solid #ffffff1f;border-radius:99px;
       padding:3px 12px;font-size:12px;margin-inline-end:6px}
.badge.ok{color:#6ee7b7;border-color:#6ee7b755}
.badge.warn{color:#fbbf24;border-color:#fbbf2455}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:14px;margin-bottom:22px}
.card{background:linear-gradient(165deg,#141e33,#101a2d);border:1px solid #ffffff14;
      border-radius:18px;padding:20px;box-shadow:0 8px 24px #00000040}
.kpi .v{font-size:34px;font-weight:900;color:#34d399;line-height:1.2}
.kpi.b .v{color:#38bdf8}.kpi.p .v{color:#a78bfa}.kpi.o .v{color:#fbbf24}.kpi.r .v{color:#f87171}
.kpi .t{color:#8ea0c0;font-size:13.5px;margin-top:4px;font-weight:700}
.sect{font-size:17px;font-weight:900;margin:26px 0 12px;display:flex;align-items:center;gap:8px}
.charts2{display:grid;grid-template-columns:1.6fr 1fr;gap:14px}
@media(max-width:760px){.charts2{grid-template-columns:1fr}}
.chartbox{background:linear-gradient(165deg,#141e33,#101a2d);border:1px solid #ffffff14;
          border-radius:18px;padding:18px;box-shadow:0 8px 24px #00000040}
.chartbox .ct{font-weight:900;font-size:15px;margin-bottom:12px}
.chartwrap{position:relative;height:260px}
.row{display:flex;align-items:center;gap:12px;margin:10px 0}
.row .pl{width:150px;font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .bar{flex:1;height:14px;background:#ffffff0d;border-radius:99px;overflow:hidden}
.row .bar i{display:block;height:100%;border-radius:99px;
            background:linear-gradient(90deg,#34d399,#38bdf8)}
.row b{width:64px;text-align:left;font-size:14px;color:#cde3ff}
/* جدول المستخدمين */
.tools{display:flex;align-items:center;gap:10px;margin:0 0 12px}
.tools input{flex:1;background:#0b1220;border:1px solid #ffffff22;color:#e8eefc;border-radius:12px;
             padding:11px 14px;font-size:14px;font-family:inherit}
.tools span{color:#8ea0c0;font-size:12.5px;white-space:nowrap}
.tblwrap{overflow-x:auto;border-radius:14px;border:1px solid #ffffff14}
table{width:100%;border-collapse:collapse;font-size:13.8px;min-width:640px}
thead th{background:#ffffff0a;color:#8ea0c0;font-size:12.5px;padding:10px 12px;text-align:right;
         white-space:nowrap;position:sticky;top:0}
tbody td{padding:10px 12px;border-top:1px solid #ffffff0a;white-space:nowrap}
tbody tr:hover{background:#ffffff06}
td.mono,span.mono{font-family:'Courier New',monospace;direction:ltr;unicode-bidi:embed;color:#7dd3fc}
td a{color:#38bdf8;text-decoration:none}
td a:hover{text-decoration:underline}
.ct-td{font-weight:900;color:#6ee7b7}
.tmuted{color:#8ea0c0;font-size:12px}
.rank{font-size:16px}
.empty{color:#8ea0c0;font-size:14px;padding:14px 4px}
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


def _sum_last_days(days, n):
    """مجموع تحميلات آخر n يوم (شامل النهارده)"""
    today = datetime.date.today()
    return sum(
        int(days.get((today - datetime.timedelta(days=i)).isoformat(), 0))
        for i in range(n)
    )


def _month_sum(days):
    """مجموع تحميلات الشهر الحالي"""
    prefix = datetime.date.today().strftime("%Y-%m")
    return sum(int(v) for k, v in days.items() if str(k).startswith(prefix))


def _last30_chart_data(days):
    """بيانات الرسم الخطي — آخر 30 يوم (تسمية + قيم)"""
    today = datetime.date.today()
    labels, data = [], []
    for i in range(29, -1, -1):
        d = today - datetime.timedelta(days=i)
        labels.append(f"{d.day}/{d.month}")
        data.append(int(days.get(d.isoformat(), 0)))
    return {"labels": labels, "data": data}


def _platform_rows(platforms):
    """أشرطة المنصات بالنِسب — أرقام دقيقة جنب الرسم الدائري"""
    if not platforms:
        return "<p class=\"empty\">لسه مفيش تحميلات مسجلة 🌱</p>"
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


def _user_table(users):
    """جدول المستخدمين الكامل: الاسم • اليوزرنيم • الآيدي • التحميلات • الاشتراك • آخر نشاط"""
    if not users:
        return "<p class=\"empty\">لسه مفيش مستخدمين 🌱</p>"

    def sort_key(kv):
        u = kv[1]
        return (-int(u.get("count", 0)), str(u.get("since") or ""))

    ranked = sorted(users.items(), key=sort_key)[:USERS_LIMIT]
    rows = []
    for i, (uid, u) in enumerate(ranked, 1):
        rank = MEDALS[i - 1] if i <= 3 else f"<span class='tmuted'>{i}</span>"
        name = _esc(u.get("name") or "—")
        username = str(u.get("username") or "").strip().lstrip("@")
        if username:
            uname = f"<a href=\"https://t.me/{_esc(username)}\" target=\"_blank\" rel=\"noopener\">@{_esc(username)}</a>"
        else:
            uname = "<span class='tmuted'>—</span>"
        cnt = int(u.get("count", 0))
        since = _esc(str(u.get("since") or "—")[:16])
        last = _esc(str(u.get("last") or "—")[:16])
        rows.append(
            f"<tr>"
            f"<td class=\"rank\">{rank}</td>"
            f"<td><b>{name}</b></td>"
            f"<td>{uname}</td>"
            f"<td class=\"mono\">{_esc(uid)}</td>"
            f"<td class=\"ct-td\">{cnt} 📥</td>"
            f"<td class=\"tmuted\">{since}</td>"
            f"<td class=\"tmuted\">{last}</td>"
            f"</tr>"
        )
    note = ""
    if len(users) > USERS_LIMIT:
        note = f"<p class=\"empty\">📘 ده أول {USERS_LIMIT} مستخدم من إجمالي {len(users)} — الأحدث بترتيب التحميلات</p>"
    return (
        "<div class=\"tools\">"
        "<input id=\"uq\" type=\"search\" placeholder=\"🔎 دوّر بالاسم أو اليوزرنيم أو الآيدي...\">"
        "<span>البحث فوري 📶</span>"
        "</div>"
        "<div class=\"tblwrap\"><table id=\"utable\">"
        "<thead><tr>"
        "<th>#</th><th>الاسم</th><th>اليوزرنيم</th><th>الآيدي</th>"
        "<th>التحميلات</th><th>اشترك في</th><th>آخر نشاط</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>" + note
    )


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
    week = _sum_last_days(days, 7)
    month = _month_sum(days)
    avg = (total / n_users) if n_users else 0.0

    chart_days = _last30_chart_data(days)
    plat_ranked = sorted(platforms.items(), key=lambda x: -x[1])
    chart_plats = {
        "labels": [k for k, _ in plat_ranked],
        "data": [int(v) for _, v in plat_ranked],
    }

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

    payload = _json.dumps({"days": chart_days, "plats": chart_plats}, ensure_ascii=False)

    return (
        "<!doctype html><html dir=\"rtl\" lang=\"ar\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<meta http-equiv=\"refresh\" content=\"60\">"
        "<title>📊 إحصائيات Migo Downloader</title>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap\" rel=\"stylesheet\">"
        "<script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js\" defer></script>"
        f"<style>{_CSS}</style></head><body><div class=\"wrap\">"
        "<h1><span class=\"logo\">🤖</span> لوحة إحصائيات البوت</h1>"
        f"<div class=\"sub\">{bot_line} • {storage_badge} <span class=\"badge\">🕐 {now_str}</span></div>"

        "<div class=\"grid\">"
        f"<div class=\"card kpi\"><div class=\"v\">{total}</div><div class=\"t\">⬇️ إجمالي التحميلات</div></div>"
        f"<div class=\"card kpi b\"><div class=\"v\">{n_users}</div><div class=\"t\">👥 المستخدمين</div></div>"
        f"<div class=\"card kpi p\"><div class=\"v\">{today}</div><div class=\"t\">🔥 تحميلات النهارده</div></div>"
        f"<div class=\"card kpi o\"><div class=\"v\">{week}</div><div class=\"t\">📅 آخر ٧ أيام</div></div>"
        f"<div class=\"card kpi r\"><div class=\"v\">{month}</div><div class=\"t\">🗓 تحميلات الشهر</div></div>"
        f"<div class=\"card kpi\"><div class=\"v\">{avg:.1f}</div><div class=\"t\">📈 متوسط لكل مستخدم</div></div>"
        "</div>"

        "<div class=\"charts2\">"
        "<div class=\"chartbox\">"
        "<div class=\"ct\">📈 التحميلات — آخر 30 يوم</div>"
        "<div class=\"chartwrap\"><canvas id=\"daysChart\"></canvas></div>"
        "</div>"
        "<div class=\"chartbox\">"
        "<div class=\"ct\">🌐 توزيع المنصات</div>"
        "<div class=\"chartwrap\"><canvas id=\"platChart\"></canvas></div>"
        "</div>"
        "</div>"

        "<div class=\"card\">"
        "<div class=\"sect\">🌐 تفصيل المنصات</div>"
        + _platform_rows(platforms) +
        "<div class=\"sect\">👥 المستخدمين — البيانات الكاملة</div>"
        + _user_table(users) +
        "</div>"

        + storage_note +
        f"<div class=\"footer\">Migo Downloader Bot • الصفحة بتتحدث تلقائياً كل 60 ثانية 🔄</div>"
        "</div>"

        f"<script id=\"pdata\" type=\"application/json\">{payload}</script>"
        "<script>"
        "(function(){"
        "var box=document.getElementById('pdata');"
        "if(!box)return;var D=JSON.parse(box.textContent);"
        "if(window.Chart){"
        "Chart.defaults.font.family=\"Cairo,'Segoe UI',Tahoma,sans-serif\";"
        "Chart.defaults.color='#8ea0c0';"
        "var grid={color:'rgba(255,255,255,.06)'};"
        "new Chart(document.getElementById('daysChart'),{"
        "type:'line',"
        "data:{labels:D.days.labels,datasets:[{label:'تحميلات',data:D.days.data,"
        "borderColor:'#34d399',backgroundColor:'rgba(52,211,153,.14)',"
        "fill:true,tension:.35,borderWidth:2.5,pointRadius:2.5,pointBackgroundColor:'#34d399'}]},"
        "options:{responsive:true,maintainAspectRatio:false,"
        "plugins:{legend:{display:false},tooltip:{rtl:true,textDirection:'rtl'}},"
        "scales:{x:{grid:grid,ticks:{maxTicksLimit:10}},y:{grid:grid,beginAtZero:true,"
        "ticks:{precision:0}}}}});"
        "new Chart(document.getElementById('platChart'),{"
        "type:'doughnut',"
        "data:{labels:D.plats.labels,datasets:[{data:D.plats.data,"
        "backgroundColor:['#34d399','#38bdf8','#a78bfa','#fbbf24','#f87171',"
        "'#f472b6','#4ade80','#fb923c','#22d3ee','#e879f9'],borderWidth:0}]},"
        "options:{responsive:true,maintainAspectRatio:false,cutout:'62%',"
        "plugins:{legend:{position:'bottom',labels:{boxWidth:12,padding:10}},"
        "tooltip:{rtl:true,textDirection:'rtl'}}}});"
        "}"
        "var q=document.getElementById('uq');"
        "if(q){q.addEventListener('input',function(){"
        "var v=q.value.trim().toLowerCase();"
        "document.querySelectorAll('#utable tbody tr').forEach(function(tr){"
        "tr.style.display=tr.textContent.toLowerCase().indexOf(v)>-1?'':'none';});});}"
        "})();"
        "</script>"
        "</body></html>"
    )
