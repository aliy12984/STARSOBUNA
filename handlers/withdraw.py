from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import create_withdraw_request, get_user_balance
from handlers.common import enforce_subscription_rules
from keyboards.contact import get_admin_contact_markup, get_admin_contact_text
from keyboards.menu import BTN_BANK, BTN_CRYPTO, BTN_MAIN_MENU, BTN_WITHDRAW, get_main_menu, get_withdraw_menu
from utils.anti_cheat import validate_user_access
from utils.ui import card, warning

router = Router()


class WithdrawStates(StatesGroup):
    waiting_for_method = State()
    waiting_for_wallet = State()
    waiting_for_amount = State()


@router.message(F.text == BTN_WITHDRAW)
async def withdraw_start(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return

        user = await validate_user_access(db, message.from_user.id)
        balance = await get_user_balance(db, user.id)
        if balance < 15.0:
            await message.reply(card("Pul Yechish", ["Minimal yechish: <b>15 stars</b>"]), reply_markup=get_main_menu())
            return

        await message.reply(
            card(
                "Pul Yechish",
                [
                    "Yechish usulini tanlang.",
                    f"Admin aloqa: <b>{get_admin_contact_text()}</b>",
                ],
            ),
            reply_markup=get_withdraw_menu(),
        )
        await state.set_state(WithdrawStates.waiting_for_method)
    except ValueError as e:
        await message.reply(str(e))


@router.message(WithdrawStates.waiting_for_method)
async def process_method(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if message.text == BTN_MAIN_MENU:
        await state.clear()
        if not await enforce_subscription_rules(message, db, bot):
            return
        await message.reply(card("Pul Yechish", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    if message.text not in [BTN_BANK, BTN_CRYPTO]:
        await message.reply(card("Pul Yechish", ["Iltimos, tugmadan tanlang."]))
        return

    await state.update_data(method=message.text)
    await message.reply(card("Manzil Kiritish", ["Karta yoki wallet ma'lumotini yuboring."]))
    await state.set_state(WithdrawStates.waiting_for_wallet)


@router.message(WithdrawStates.waiting_for_wallet)
async def process_wallet(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if message.text == BTN_MAIN_MENU:
        await state.clear()
        if not await enforce_subscription_rules(message, db, bot):
            return
        await message.reply(card("Pul Yechish", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    wallet = message.text.strip()
    if not wallet:
        await message.reply(warning("To'g'ri ma'lumot kiriting."))
        return

    await state.update_data(wallet=wallet)
    user = await validate_user_access(db, message.from_user.id)
    balance = await get_user_balance(db, user.id)
    await message.reply(
        card(
            "Miqdor Kiritish",
            [
                f"Balans: <b>{balance:.2f} stars</b>",
                "Qancha yechasiz? (min 15 stars)",
            ],
        )
    )
    await state.set_state(WithdrawStates.waiting_for_amount)


@router.message(WithdrawStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if message.text == BTN_MAIN_MENU:
        await state.clear()
        if not await enforce_subscription_rules(message, db, bot):
            return
        await message.reply(card("Pul Yechish", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    try:
        amount = float(message.text.strip())
        if amount < 15.0:
            raise ValueError
    except ValueError:
        await message.reply(warning("Miqdor noto'g'ri. Minimal 15 stars."))
        return

    user = await validate_user_access(db, message.from_user.id)
    balance = await get_user_balance(db, user.id)
    if amount > balance:
        await message.reply(warning("Balans yetarli emas."))
        await state.clear()
        return

    data = await state.get_data()
    await create_withdraw_request(db, user.id, amount, data["wallet"])
    await message.reply(
        card(
            "Yechish So'rovi Yuborildi",
            [
                f"Miqdor: <b>{amount:.2f} stars</b>",
                f"Manzil: <code>{data['wallet']}</code>",
                f"Aloqa: <b>{get_admin_contact_text()}</b>",
            ],
            "So'rov admin tomonidan ko'rib chiqiladi.",
        ),
        reply_markup=get_main_menu(),
    )
    contact_markup = get_admin_contact_markup()
    if contact_markup:
        await message.reply(card("Admin Aloqa", ["Pul yechish bo'yicha bog'laning."]), reply_markup=contact_markup)
    await state.clear()
