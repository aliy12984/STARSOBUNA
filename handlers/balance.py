import random

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import can_claim_daily_bonus, claim_daily_bonus, get_user_balance, get_user_stats
from handlers.common import enforce_subscription_rules
from keyboards.contact import get_admin_contact_text
from keyboards.menu import BTN_BALANCE, BTN_DAILY_BONUS, BTN_HELP, BTN_STATS, get_main_menu
from utils.anti_cheat import validate_user_access
from utils.reward_system import add_daily_bonus
from utils.ui import card, info, success

router = Router()


@router.message(F.text == BTN_BALANCE)
async def my_balance(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return
        user = await validate_user_access(db, message.from_user.id)
        balance = await get_user_balance(db, user.id)
        await message.reply(
            card(
                "Mening Balansim",
                [
                    f"Joriy balans: <b>{balance:.2f} stars</b>",
                    "Minimal yechish: <b>15 stars</b>",
                ],
            ),
            reply_markup=get_main_menu(),
        )
    except ValueError as e:
        await message.reply(str(e))


@router.message(F.text == BTN_DAILY_BONUS)
async def daily_bonus(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return
        user = await validate_user_access(db, message.from_user.id)
        if not await can_claim_daily_bonus(db, user.id):
            await message.reply(info("Kunlik bonus 24 soatda bir marta beriladi."), reply_markup=get_main_menu())
            return

        from database.queries import get_setting_float

        max_bonus = await get_setting_float(db, "daily_bonus_max", 1.00)
        bonus = round(random.uniform(0, max_bonus), 2)
        await claim_daily_bonus(db, user.id)
        await add_daily_bonus(db, user.id, bonus)
        await message.reply(
            card(
                "Kunlik Bonus",
                [f"Balansga qo'shildi: <b>+{bonus:.2f} stars</b>"],
                success("Bonus muvaffaqiyatli berildi."),
            ),
            reply_markup=get_main_menu(),
        )
    except ValueError as e:
        await message.reply(str(e))


@router.message(F.text == BTN_STATS)
async def statistics(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return
        user = await validate_user_access(db, message.from_user.id)
        stats = await get_user_stats(db, user.id)
        text = card(
                "Statistika",
                [
                    f"Jami ishlab topilgan: <b>{stats['total_earned']:.2f} stars</b>",
                    f"Jami sarflangan: <b>{stats['total_spent']:.2f} stars</b>",
                    f"Bajarilgan vazifalar: <b>{stats['completed_tasks']}</b>",
                    f"Referrallar: <b>{stats['referrals']}</b>",
                ],
        )
        await message.reply(text, reply_markup=get_main_menu())
    except ValueError as e:
        await message.reply(str(e))


@router.message(F.text == BTN_HELP)
async def help_command(message: Message):
    admin_contact = get_admin_contact_text()
    text = card(
        "Yordam Markazi",
        [
            "Pul ishlash: kanallarga obuna bo'lib vazifa bajarish",
            "Buyurtma berish: kanalga obunachi buyurtma qilish",
            "Referral: do'st taklif qilib bonus olish",
            "Pul yechish: balansdan yechish so'rovi yuborish",
            f"Admin aloqa: <b>{admin_contact}</b>",
        ],
        "Kerakli bo'limni menyudan tanlang.",
    )
    await message.reply(text, reply_markup=get_main_menu())
