from __future__ import annotations

RULE = "━━━━━━━━━━━━━━━━━━━━━━"

TITLE_ICONS = {
    "Xush kelibsiz": "🚀",
    "Qaytganingizdan xursandmiz": "👋",
    "Majburiy Obuna": "🔐",
    "Kanal Ro'yxati": "📡",
    "Asosiy Menyu": "🏠",
    "Vazifa Kartasi": "🎯",
    "Kanal Havolasi": "🔗",
    "Skip Cheklovi": "⏳",
    "Limit Tugadi": "⛔",
    "Tekshirish Natijasi": "🔎",
    "Vazifa Tasdiqlandi": "✅",
    "Vazifalar": "📭",
    "Yangi Buyurtma": "📦",
    "Buyurtma": "🧾",
    "Buyurtma Tasdiqlash": "🧮",
    "Buyurtma Yaratildi": "✅",
    "Mening Buyurtmalarim": "📊",
    "Mening Balansim": "💳",
    "Kunlik Bonus": "🎁",
    "Statistika": "📈",
    "Yordam Markazi": "🛟",
    "Referral Dastur": "🤝",
    "Hisobni To'ldirish": "💰",
    "Stars Kiritish": "⭐",
    "Naxt Kiritish": "💵",
    "Miqdor Qabul Qilindi": "🧾",
    "Izoh Yuborish": "✍️",
    "Topup So'rovi Yuborildi": "📨",
    "Pul Yechish": "🏧",
    "Manzil Kiritish": "🗂",
    "Miqdor Kiritish": "🔢",
    "Yechish So'rovi Yuborildi": "📨",
    "Admin Panel": "🛠",
    "Admin Statistika": "📊",
    "Task Kanal Qo'shish": "➕",
    "Majburiy Kanal Qo'shish": "📌",
    "Majburiy Kanal O'chirish": "🗑",
    "Topup So'rovlari": "📥",
    "To'ldirish So'rovlari": "📥",
    "Yechish So'rovlari": "📤",
    "Broadcast": "📢",
    "Balans Qo'shish": "➕",
    "Balans Ayirish": "➖",
    "Ban Qilish": "🔒",
    "Obuna Tasdiqlandi": "✅",
}


def card(title: str, lines: list[str] | None = None, footer: str | None = None) -> str:
    icon = TITLE_ICONS.get(title, "✨")
    parts = [f"<b>{icon} {title}</b>", f"<code>{RULE}</code>"]
    if lines:
        parts.extend(lines)
    if footer:
        parts.extend(["", footer])
    return "\n".join(parts)


def success(text: str) -> str:
    return f"<b>[OK]</b> {text}"


def info(text: str) -> str:
    return f"<b>[INFO]</b> {text}"


def warning(text: str) -> str:
    return f"<b>[WARN]</b> {text}"


def error(text: str) -> str:
    return f"<b>[ERROR]</b> {text}"


def progress_bar(current: int, total: int, width: int = 16) -> str:
    if total <= 0:
        total = 1
    ratio = max(0.0, min(float(current) / float(total), 1.0))
    filled = int(round(ratio * width))
    bar = "#" * filled + "." * (width - filled)
    percent = int(round(ratio * 100))
    return f"<code>[{bar}]</code> <b>{percent}%</b>"
