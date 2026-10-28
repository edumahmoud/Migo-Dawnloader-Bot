"""إحصائيات التحميل — محفوظة في ملف JSON"""
import html
import json
import os
import threading

import config


class Stats:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.data = {"total": 0, "platforms": {}, "users": {}}
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
            self._save()

    def user_ids(self):
        with self.lock:
            return [int(k) for k in self.data["users"].keys() if str(k).isdigit()]

    def summary_text(self, full=False, bot_username=""):
        with self.lock:
            total = self.data["total"]
            platforms = dict(self.data["platforms"])
            users = dict(self.data["users"])
        lines = ["📊 <b>إحصائيات البوت</b>", ""]
        lines.append(f"⬇️ إجمالي التحميلات: <b>{total}</b>")
        lines.append(f"👥 عدد المستخدمين: <b>{len(users)}</b>")
        if platforms:
            lines.append("")
            lines.append("<b>حسب المنصة:</b>")
            for name, cnt in sorted(platforms.items(), key=lambda x: -x[1]):
                lines.append(f"• {name}: <b>{cnt}</b>")
        if full and users:
            lines.append("")
            lines.append("<b>🏆 أكثر المستخدمين:</b>")
            top = sorted(users.items(), key=lambda kv: -kv[1].get("count", 0))[:10]
            for i, (uid, u) in enumerate(top, 1):
                nm = html.escape(str(u.get("name") or "مستخدم"))
                lines.append(f"{i}. {nm} — <b>{u.get('count', 0)}</b> 📥")
        if bot_username:
            lines.append("")
            lines.append(f"🤖 @{bot_username}")
        return "\n".join(lines)


stats = Stats(os.path.join(config.DATA_DIR, "stats.json"))
