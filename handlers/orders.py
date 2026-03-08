from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import get_order_progress, get_orders_by_user, get_setting_float, get_user_balance
from handlers.common import enforce_subscription_rules
from keyboards.menu import (
    BTN_CANCEL,
    BTN_CONFIRM_ORDER,
    BTN_MAIN_MENU,
    BTN_MY_ORDERS,
    BTN_ORDER,
    MAIN_MENU_BUTTONS,
    get_main_menu,
    get_order_menu,
)
from services.order_service import OrderService
from utils.anti_cheat import validate_user_access
from utils.ui import card, progress_bar, success

router = Router()
MY_ORDERS_REFRESH_CB = "my_orders_refresh"


class OrderStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_subscribers = State()
    waiting_for_confirmation = State()


def _my_orders_refresh_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Yangilash", callback_data=MY_ORDERS_REFRESH_CB)]]
    )


def _order_status_label(status: str) -> str:
    mapping = {
        "active": "Faol",
        "completed": "Bajarildi",
        "refunded": "Refund qilindi",
        "pending": "Kutilmoqda",
    }
    return mapping.get(status, status)


async def _build_my_orders_text(db: AsyncSession, user_id: int) -> str:
    orders = await get_orders_by_user(db, user_id, limit=20)
    if not orders:
        return card("Mening Buyurtmalarim", ["Sizda hozircha buyurtmalar yo'q."])

    blocks = []
    for order in orders:
        progress = await get_order_progress(db, order.id)
        needed = int(progress["needed"]) if progress else int(order.subscribers_needed or 0)
        completed = int(progress["completed"]) if progress else 0
        remaining = int(progress["remaining"]) if progress else max(needed - completed, 0)
        status = _order_status_label(progress["status"] if progress else order.status)
        blocks.append(
            (
                f"Buyurtma ID: <b>{order.id}</b>\n"
                f"Status: <b>{status}</b>\n"
                f"Progress: <b>{completed}/{needed}</b>\n"
                f"{progress_bar(completed, needed)}\n"
                f"Qoldi: <b>{remaining}</b>\n"
                "<code>------------------------------</code>"
            )
        )

    return card("Mening Buyurtmalarim", blocks, "Yangilash uchun tugmani bosing.")


@router.message(F.text == BTN_MY_ORDERS)
async def my_orders(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return
        user = await validate_user_access(db, message.from_user.id)
        text = await _build_my_orders_text(db, user.id)
        await message.reply(text, reply_markup=_my_orders_refresh_markup())
    except ValueError as e:
        await message.reply(str(e), reply_markup=get_main_menu())


@router.callback_query(F.data == MY_ORDERS_REFRESH_CB)
async def my_orders_refresh(callback: CallbackQuery, db: AsyncSession, bot: Bot):
    if not callback.message:
        await callback.answer()
        return
    if not await enforce_subscription_rules(callback.message, db, bot):
        await callback.answer("Avval majburiy obunani tasdiqlang.", show_alert=True)
        return
    try:
        user = await validate_user_access(db, callback.from_user.id)
        text = await _build_my_orders_text(db, user.id)
        await callback.message.edit_text(text, reply_markup=_my_orders_refresh_markup())
        await callback.answer("Yangilandi")
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)


@router.message(F.text == BTN_ORDER)
async def create_order_start(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return
        user = await validate_user_access(db, message.from_user.id)
        balance = await get_user_balance(db, user.id)
        if balance < 15.0:
            await message.reply(
                card("Buyurtma", ["Buyurtma berish uchun balansda kamida <b>15 stars</b> bo'lishi kerak."]),
                reply_markup=get_main_menu(),
            )
            return
        await message.reply(
            card(
                "Yangi Buyurtma",
                [
                    "Kanal username kiriting (@ bilan).",
                    "Masalan: <code>@my_channel</code>",
                ],
            ),
            reply_markup=None,
        )
        await state.set_state(OrderStates.waiting_for_channel)
    except ValueError as e:
        await message.reply(str(e), reply_markup=get_main_menu())


@router.message(OrderStates.waiting_for_channel)
async def process_channel(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if message.text in MAIN_MENU_BUTTONS:
        await state.clear()
        if not await enforce_subscription_rules(message, db, bot):
            return
        await message.reply(card("Buyurtma", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    channel_username = message.text.strip()
    if not channel_username.startswith("@"):
        await message.reply(card("Xatolik", ["Username @ bilan boshlanishi kerak."]))
        return

    order_service = OrderService(db, bot)
    if not await order_service.check_bot_admin(channel_username):
        await message.reply(card("Xatolik", ["Bot bu kanalda admin emas.", "Avval botni admin qiling."]))
        await state.clear()
        return

    await state.update_data(channel_username=channel_username)
    await message.reply(card("Obunachi Soni", ["Nechta obunachi kerak?", "Masalan: <code>100</code>"]))
    await state.set_state(OrderStates.waiting_for_subscribers)


@router.message(OrderStates.waiting_for_subscribers)
async def process_subscribers(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if message.text in MAIN_MENU_BUTTONS:
        await state.clear()
        if not await enforce_subscription_rules(message, db, bot):
            return
        await message.reply(card("Buyurtma", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    try:
        subscribers = int(message.text.strip())
        if subscribers < 20:
            raise ValueError
    except ValueError:
        await message.reply(card("Xatolik", ["Minimal obunachi soni: <b>20</b> ta."]))
        return

    data = await state.get_data()
    channel_username = data["channel_username"]

    subscriber_price = await get_setting_float(db, "subscriber_price", 0.30)
    price = subscribers * subscriber_price
    await state.update_data(subscribers=subscribers, price=price)
    await message.reply(
        card(
            "Buyurtma Tasdiqlash",
            [
                f"Kanal: <b>{channel_username}</b>",
                f"Obunachi: <b>{subscribers}</b>",
                f"To'lov: <b>{price:.2f} stars</b>",
            ],
            "Tasdiqlaysizmi?",
        ),
        reply_markup=get_order_menu(),
    )
    await state.set_state(OrderStates.waiting_for_confirmation)


@router.message(OrderStates.waiting_for_confirmation, F.text == BTN_CONFIRM_ORDER)
async def confirm_order(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    try:
        user = await validate_user_access(db, message.from_user.id)
        data = await state.get_data()
        order_service = OrderService(db, bot)
        result = await order_service.create_order(user.id, data["channel_username"], data["subscribers"])
        await message.reply(
            card(
                "Buyurtma Yaratildi",
                [
                    f"ID: <b>{result['order_id']}</b>",
                    f"Obunachi: <b>{result['subscribers']}</b>",
                    f"To'lov: <b>{result['price']:.2f} stars</b>",
                ],
                success("Buyurtma muvaffaqiyatli yaratildi."),
            ),
            reply_markup=get_main_menu(),
        )
    except ValueError as e:
        await message.reply(str(e), reply_markup=get_main_menu())
    finally:
        await state.clear()


@router.message(OrderStates.waiting_for_confirmation, F.text == BTN_CANCEL)
async def cancel_order(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if not await enforce_subscription_rules(message, db, bot):
        await state.clear()
        return
    await message.reply(card("Buyurtma", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
    await state.clear()


@router.message(OrderStates.waiting_for_confirmation)
async def handle_confirmation_menu(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if message.text in MAIN_MENU_BUTTONS:
        await state.clear()
        if not await enforce_subscription_rules(message, db, bot):
            return
        await message.reply(card("Buyurtma", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return
    await message.reply(
        card("Buyurtma Tasdiqlash", ["Iltimos, tasdiqlash yoki bekor qilish tugmasidan foydalaning."]),
        reply_markup=get_order_menu(),
    )
