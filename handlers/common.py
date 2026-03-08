from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import get_user_by_telegram_id
from keyboards.mandatory import get_mandatory_subscription_keyboard
from services.order_service import OrderService
from utils.subscription_checker import (
    get_unsubscribed_mandatory_channels,
    process_unsubscribe_penalties,
)
from utils.ui import card


async def send_mandatory_gate_message(message: Message, channels: list[dict[str, str | None]]):
    text = card("Majburiy Obuna", ["Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling."])
    channel_lines = [f"- {channel.get('display') or channel.get('channel_ref')}" for channel in channels]
    await message.reply(
        text,
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.reply(
        card("Kanal Ro'yxati", channel_lines, "Obuna bo'lgach, pastdagi tekshirish tugmasini bosing."),
        reply_markup=get_mandatory_subscription_keyboard(channels),
    )


async def enforce_subscription_rules(message: Message, db: AsyncSession, bot) -> bool:
    telegram_id = message.from_user.id
    user = await get_user_by_telegram_id(db, telegram_id)
    if user:
        await process_unsubscribe_penalties(db, bot, user.id, telegram_id)
        order_service = OrderService(db, bot)
        refunded = await order_service.process_auto_refunds_for_user(user.id)
        if refunded:
            lines = []
            for item in refunded[:5]:
                lines.append(
                    (
                        f"Order #{item['order_id']}: qoldi {item['remaining']} ta, "
                        f"refund +{item['refund_amount']:.2f} stars"
                    )
                )
            await message.reply(
                card(
                    "Auto Refund",
                    lines,
                    "Buyurtma uzoq vaqt faol bo'lmagani uchun qisman refund qilindi.",
                )
            )
    missing_channels = await get_unsubscribed_mandatory_channels(db, bot, telegram_id)
    if not missing_channels:
        return True

    await send_mandatory_gate_message(message, missing_channels)
    return False
