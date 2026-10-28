"""أدوات مساعدة صغيرة"""


def fmt_size(n):
    """تحويل البايتات لنص مقروء: 12.3MB"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "0B"
    if n <= 0:
        return "0B"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{int(n)}B" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def fmt_duration(sec):
    """تحويل الثواني لمدة مقروءة: 3:05 أو 1:02:33"""
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return "—"
    if sec <= 0:
        return "—"
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
