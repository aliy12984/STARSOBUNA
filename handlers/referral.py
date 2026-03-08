from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.common import enforce_subscription_rules
from keyboards.menu import BTN_REFERRAL, get_main_menu
from services.referral_service import ReferralService
from utils.anti_cheat import validate_user_access
from utils.ui import card

router = Router()


@router.message(F.text == BTN_REFERRAL)
async def referral_program(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return

        user = await validate_user_access(db, message.from_user.id)
        referral_service = ReferralService(db)
        referral_link = referral_service.generate_referral_link(user.telegram_id)

        from database.queries import get_setting_float

        referral_reward = await get_setting_float(db, "referral_reward", 0.10)
        text = card(
            "Referral Dastur",
            [
                f"Sizning linkingiz:\n<code>{referral_link}</code>",
                f"Har bir yangi referral uchun: <b>{referral_reward:.2f} stars</b>",
                "Do'stingiz botga kirsa mukofot avtomatik qo'shiladi.",
            ],
            "Linkni nusxalab ulashing.",
        )
        await message.reply(text, reply_markup=get_main_menu())
    except ValueError as e:
        await message.reply(str(e))
