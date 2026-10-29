"""إحصائيات التحميل — محفوظة في ملف JSON + نسخة دائمة في قناة تليجرام

على Vercel الملف المحلي بيتمسح كل ما السيرفر ينعش، فلما نظبط STATS_CHAT_ID
(قناة خاصة فيها البوت أدمن) البوت بيخزن آخر نسخة هناك ويقراها عند الصحوة.
"""
import html
import io
import json
import logging
import os
import threading
import time

import config
from utils import LINE

MEDALS = ("🥇", "🥈", "🥉")
STATS_PREFIX = "MIGO_STATS:"  # علامة رسالة المؤشر المثبتة اللي فيها file_id آخر نسخة
log = logging.getLogger("stats")


class Stats:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.data = {"total": 0, "platforms": {}, "users": {}, "days": {}}
        self.storage_chat = config.STATS_CHAT_ID  # 0 = مفيش تخزين دائم
        self._last_sync = 0.0
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        except OSError:
            pass
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data = {
                    "total": int(loaded.get("total") or 0),
                    "platforms": dict(loaded.get("platforms") or {}),
                    "users": dict(loaded.get("users") or {}),
                    "days": dict(loaded.get("days") or {}),
                }
        except Exception:
            pass

    def _save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def record(self, user_id, name, platform):
        with self.lock:
            self.data["total"] += 1
            self.data["platforms"][platform] = self.data["platforms"].get(platform, 0) + 1
            u = self.data["users"].setdefault(str(user_id), {"name": "", "count": 0})
            u["name"] = name or u.get("name") or ""
            u["count"] += 1
            day = time.strftime("%Y-%m-%d")
            self.data["days"][day] = self.data["days"].get(day, 0) + 1
            self._save()

    def user_ids(self):
        with self.lock:
            return [int(k) for k in self.data["users"].keys() if str(k).isdigit()]

    def total_count(self):
        """إجمالي التحميلات — لسطر الإحصائيات السريع في بطاقة الفيديو"""
        with self.lock:
            return self.data["total"]

    def user_count(self):
        """عدد المستخدمين المسجلين"""
        with self.lock:
            return len(self.data["users"])

    def user_downloads(self, user_id):
        """عدد تحميلات مستخدم معين (لرسالة النجاح: ده تحميلك رقم كام)"""
        with self.lock:
            u = self.data["users"].get(str(user_id))
            return int((u or {}).get("count", 0))

    def snapshot(self):
        """نسخة كاملة من البيانات (للوحة الويب) — آمنة للقراءة من أي حتة"""
        with self.lock:
            return json.loads(json.dumps(self.data))

    # ─────────── التخزين الدائم في قناة تليجرام ───────────

    async def load_from_telegram(self, bot):
        """حمّل آخر نسخة إحصائيات من قناة التخزين — أول ما السيرفر يصحى (مرة واحدة)

        الرسالة المثبتة في القناة فيها file_id لآخر ملف stats.json — بنقراه ونحمّله.
        لو حصل أي مشكلة بنكمل بالبيانات المحلية عادي (مفيش كراش أبداً).
        """
        if not (self.storage_chat and bot):
            return
        try:
            chat = await bot.get_chat(self.storage_chat)
            pin = chat.pinned_message
            if not pin or not pin.text or not pin.text.startswith(STATS_PREFIX):
                return
            fid = pin.text.split(":", 1)[1].strip()
            tg_file = await bot.get_file(fid)
            buf = io.BytesIO()
            await tg_file.download_to_memory(buf)
            remote = json.loads(buf.getvalue().decode("utf-8"))
            if not isinstance(remote, dict):
                return
            clean = {
                "total": int(remote.get("total") or 0),
                "platforms": {str(k): int(v) for k, v in (remote.get("platforms") or {}).items()},
                "users": {str(k): u for k, u in (remote.get("users") or {}).items() if isinstance(u, dict)},
                "days": {str(k): int(v) for k, v in (remote.get("days") or {}).items()},
            }
            with self.lock:
                # نستبدل لو النسخة البُعد أحدث (يعني إجمالي أكبر أو يساوي المحلي)
                if clean["total"] >= self.data["total"]:
                    self.data = clean
                    self._save()
            log.info("stats loaded from storage chat: total=%s", clean["total"])
        except Exception as e:  # noqa: BLE001
            log.warning("stats remote load failed (هكمل بالبيانات المحلية): %s", e)

    async def maybe_sync(self, bot):
        """ارفع نسخة الإحصائيات لقناة التخزين — مرة واحدة كل دقيقة على الأكثر"""
        if not (self.storage_chat and bot):
            return
        now = time.time()
        if now - self._last_sync < 60:
            return
        self._last_sync = now
        try:
            await self._save_remote(bot)
        except Exception as e:  # noqa: BLE001
            log.warning("stats remote sync failed: %s", e)

    async def _save_remote(self, bot):
        """ارفع stats.json للقناة وحدّث الرسالة المثبتة بآخر file_id"""
        with self.lock:
            payload = json.dumps(self.data, ensure_ascii=False, indent=1).encode("utf-8")
        doc = await bot.send_document(self.storage_chat, document=payload, filename="stats.json")
        fid = doc.document.file_id
        text = STATS_PREFIX + fid
        pin = None
        try:
            chat = await bot.get_chat(self.storage_chat)
            pin = chat.pinned_message
        except Exception:  # noqa: BLE001
            pin = None
        if pin and pin.text and pin.text.startswith(STATS_PREFIX):
            await bot.edit_message_text(text, chat_id=self.storage_chat, message_id=pin.message_id)
        else:
            pointer = await bot.send_message(self.storage_chat, text)
            await bot.pin_chat_message(self.storage_chat, pointer.message_id, disable_notification=True)

    def summary_text(self, full=False, bot_username=""):
        with self.lock:
            total = self.data["total"]
            platforms = dict(self.data["platforms"])
            users = dict(self.data["users"])
        n_users = len(users)
        days = dict(self.data.get("days") or {})
        today = days.get(time.strftime("%Y-%m-%d"), 0)
        lines = ["📊 <b>إحصائيات البوت</b> 📈", LINE, ""]
        lines.append(f"⬇️ إجمالي التحميلات: <b>{total}</b>")
        lines.append(f"🔥 تحميلات النهارده: <b>{today}</b>")
        lines.append(f"👥 عدد المستخدمين: <b>{n_users}</b>")
        if n_users:
            avg = total / n_users
            lines.append(f"📈 متوسط التحميل لكل مستخدم: <b>{avg:.1f}</b>")
        if platforms:
            lines.append("")
            lines.append("🟦 <b>حسب المنصة:</b>")
            ranked = sorted(platforms.items(), key=lambda x: -x[1])
            for i, (name, cnt) in enumerate(ranked):
                medal = MEDALS[i] if i < 3 else "▫️"
                lines.append(f"{medal} {name}: <b>{cnt}</b>")
        if full and users:
            lines.append("")
            lines.append("🏆 <b>أكثر المستخدمين:</b>")
            top = sorted(users.items(), key=lambda kv: -kv[1].get("count", 0))[:10]
            for i, (uid, u) in enumerate(top, 1):
                nm = html.escape(str(u.get("name") or "مستخدم"))
                medal = MEDALS[i - 1] if i <= 3 else f"{i}."
                lines.append(f"{medal} {nm} — <b>{u.get('count', 0)}</b> 📥")
        if bot_username:
            lines.append("")
            lines.append(LINE)
            lines.append(f"🤖 @{bot_username}")
        return "\n".join(lines)


stats = Stats(os.path.join(config.DATA_DIR, "stats.json"))
