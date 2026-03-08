from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import create_user, get_user_by_telegram_id
from handlers.common import send_mandatory_gate_message
from keyboards.mandatory import BTN_CHECK_MANDATORY, BTN_NO_LINK, get_mandatory_subscription_keyboard
from keyboards.menu import get_main_menu
from services.referral_service import ReferralService
from utils.anti_cheat import is_user_banned
from utils.subscription_checker import get_unsubscribed_mandatory_channels
from utils.ui import card, success, warning

router = Router()


@router.message(Command("start"))
async def start_command(message: Message, db: AsyncSession, bot):
    telegram_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name or "Foydalanuvchi"

    if await is_user_banned(db, telegram_id):
        await message.reply(warning("Siz bu botdan foydalanish uchun bloklangansiz."))
        return

    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        referrer_user_id = None
        referrer_telegram_id = None
        parts = message.text.split()
        if len(parts) > 1:
            try:
                referrer_telegram_id = int(parts[1])
            except ValueError:
                referrer_telegram_id = None
        if referrer_telegram_id == telegram_id:
            referrer_telegram_id = None
        if referrer_telegram_id:
            referrer = await get_user_by_telegram_id(db, referrer_telegram_id)
            referrer_user_id = referrer.id if referrer else None

        user = await create_user(db, telegram_id, username, first_name, referrer_user_id)
        if referrer_telegram_id:
            referral_service = ReferralService(db)
            await referral_service.process_referral_join(user.id, referrer_telegram_id)
        welcome_text = card(
            "Xush kelibsiz",
            [
                f"Salom, <b>{first_name}</b>!",
                "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.",
                "Botdan foydalanish uchun pastdagi menyudan bo'lim tanlang.",
                "Asosiy yo'nalishlar: vazifa, buyurtma, referral, balans.",
            ],
        )
    else:
        welcome_text = card(
            "Qaytganingizdan xursandmiz",
            [
                f"Salom, <b>{first_name}</b>!",
                "Ishni davom ettirish uchun menyudan bo'lim tanlang.",
                "Yordam bo'limida barcha qo'llanma mavjud.",
            ],
        )

    missing_channels = await get_unsubscribed_mandatory_channels(db, bot, telegram_id)
    if missing_channels:
        await message.reply(welcome_text, reply_markup=ReplyKeyboardRemove())
        await send_mandatory_gate_message(message, missing_channels)
        return

    await message.reply(welcome_text, reply_markup=get_main_menu())


@router.callback_query(F.data == BTN_CHECK_MANDATORY)
async def verify_mandatory_subscriptions(callback: CallbackQuery, db: AsyncSession, bot):
    missing_channels = await get_unsubscribed_mandatory_channels(db, bot, callback.from_user.id)
    if missing_channels:
        await callback.answer("Hali barcha kanalga obuna bo'linmagan.", show_alert=True)
        if callback.message:
            lines = [f"- {item.get('display') or item.get('channel_ref')}" for item in missing_channels]
            await callback.message.edit_text(
                card(
                    "Majburiy Obuna",
                    lines,
                    "Barcha kanallarga obuna bo'lgach, qayta tekshiring.",
                ),
                reply_markup=get_mandatory_subscription_keyboard(missing_channels),
            )
        return

    await callback.answer("Obuna tasdiqlandi.")
    if callback.message:
        await callback.message.answer(
            card("Obuna Tasdiqlandi", ["Barcha majburiy kanallar tekshirildi.", "Asosiy menyu ochildi."], success("Tayyor.")),
            reply_markup=get_main_menu(),
        )


@router.callback_query(F.data == BTN_NO_LINK)
async def mandatory_channel_no_link(callback: CallbackQuery):
    await callback.answer("Bu kanal uchun join-link yo'q. Admin bilan bog'laning.", show_alert=True)
