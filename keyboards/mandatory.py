from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BTN_CHECK_MANDATORY = "check_mandatory_subscriptions"
BTN_NO_LINK = "mandatory_no_link"


def _to_channel_url(channel_ref: str, join_link: str | None) -> str | None:
    if join_link:
        value = join_link.strip()
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if value.startswith("t.me/"):
            return f"https://{value}"

    value = channel_ref.strip()
    if value.lstrip("-").isdigit():
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return f"https://t.me/{value.lstrip('@')}"


def get_mandatory_subscription_keyboard(channels: list[dict[str, str | None]]) -> InlineKeyboardMarkup:
    rows = []
    for idx, channel in enumerate(channels, start=1):
        display = channel.get("display") or channel.get("channel_ref") or f"Kanal {idx}"
        url = _to_channel_url(channel.get("channel_ref", ""), channel.get("join_link"))
        if url:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"🔗 {idx}. Kanalga kirish: {display}",
                        url=url,
                    )
                ]
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"❗ {idx}. Link yo'q: {display}",
                        callback_data=BTN_NO_LINK,
                    )
                ]
            )

    rows.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data=BTN_CHECK_MANDATORY)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
