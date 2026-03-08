from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import config


def _resolve_admin_contact_url() -> str | None:
    contact = (config.ADMIN_CONTACT or "").strip()
    if contact:
        if contact.startswith("https://") or contact.startswith("http://"):
            return contact
        if contact.startswith("t.me/"):
            return f"https://{contact}"
        if contact.startswith("@"):
            return f"https://t.me/{contact.lstrip('@')}"
        if contact.isdigit():
            return f"tg://user?id={contact}"
        return contact

    if config.ADMIN_IDS:
        return f"tg://user?id={config.ADMIN_IDS[0]}"
    return None


def get_admin_contact_text() -> str:
    contact = (config.ADMIN_CONTACT or "").strip()
    if contact:
        if contact.startswith("https://t.me/"):
            username = contact.rstrip("/").split("/")[-1]
            return f"@{username}" if username else contact
        return contact
    if config.ADMIN_IDS:
        return f"Admin ID: {config.ADMIN_IDS[0]}"
    return "Admin"


def get_admin_contact_markup() -> InlineKeyboardMarkup | None:
    url = _resolve_admin_contact_url()
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="👤 Admin bilan aloqa", url=url)]]
    )
