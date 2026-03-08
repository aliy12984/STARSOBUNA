from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import create_topup_request, get_setting_float
from handlers.common import enforce_subscription_rules
from keyboards.contact import get_admin_contact_markup, get_admin_contact_text
from keyboards.menu import BTN_MAIN_MENU, BTN_TOPUP, MAIN_MENU_BUTTONS, get_main_menu
from utils.anti_cheat import validate_user_access
from utils.ui import card, error, success

router = Router()

BTN_TOPUP_STARS = "⭐ Stars bilan to'ldirish"
BTN_TOPUP_CASH = "💵 Naxt bilan to'ldirish"


class TopupStates(StatesGroup):
    waiting_for_method = State()
    waiting_for_amount = State()
    waiting_for_note = State()


def _topup_method_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TOPUP_STARS), KeyboardButton(text=BTN_TOPUP_CASH)],
            [KeyboardButton(text=BTN_MAIN_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Kiritish turini tanlang...",
    )


def _cash_to_stars(amount_uzs: float, rate_100: float) -> float:
    if rate_100 <= 0:
        return 0.0
    return round((amount_uzs * 100.0) / rate_100, 2)


@router.message(F.text == BTN_TOPUP)
async def topup_start(message: Message, state: FSMContext, db: AsyncSession, bot: Bot):
    if not await enforce_subscription_rules(message, db, bot):
        return
    await validate_user_access(db, message.from_user.id)
    rate_100 = await get_setting_float(db, "stars_rate_100", 25000.0)
    await message.reply(
        card(
            "Hisobni To'ldirish",
            [
                f"Kurs: <b>100 stars = {rate_100:,.0f} so'm</b>",
                "Stars bo'yicha minimum: <b>15 stars</b>",
                "Naxt bo'yicha minimum: <b>5000 so'm</b>",
                f"Admin aloqa: <b>{get_admin_contact_text()}</b>",
            ],
            "Kiritish turini tanlang.",
        ),
        reply_markup=_topup_method_menu(),
    )
    await state.set_state(TopupStates.waiting_for_method)


@router.message(TopupStates.waiting_for_method)
async def topup_method(message: Message, state: FSMContext):
    if message.text == BTN_MAIN_MENU:
        await state.clear()
        await message.reply(card("Hisobni To'ldirish", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    if message.text not in {BTN_TOPUP_STARS, BTN_TOPUP_CASH}:
        await message.reply(error("Iltimos, tugmadan tanlang."), reply_markup=_topup_method_menu())
        return

    method = "stars" if message.text == BTN_TOPUP_STARS else "cash"
    await state.update_data(payment_method=method)
    if method == "stars":
        await message.reply(
            card(
                "Stars Kiritish",
                [
                    "Miqdor kiriting.",
                    "Minimum: <b>15 stars</b>",
                ],
                "Masalan: <code>25</code>",
            ),
            reply_markup=None,
        )
    else:
        await message.reply(
            card(
                "Naxt Kiritish",
                [
                    "Miqdor kiriting.",
                    "Minimum: <b>5000 so'm</b>",
                ],
                "Masalan: <code>25000</code>",
            ),
            reply_markup=None,
        )
    await state.set_state(TopupStates.waiting_for_amount)


@router.message(TopupStates.waiting_for_amount)
async def topup_amount(message: Message, state: FSMContext, db: AsyncSession):
    if message.text in MAIN_MENU_BUTTONS:
        await state.clear()
        await message.reply(card("Hisobni To'ldirish", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    data = await state.get_data()
    method = data.get("payment_method", "cash")
    try:
        amount = float((message.text or "").replace(",", "").strip())
        if amount <= 0:
            raise ValueError
        if method == "stars" and amount < 15:
            await message.reply(error("Minimum stars miqdori: <b>15</b>"))
            return
        if method == "cash" and amount < 5000:
            await message.reply(error("Minimum naxt miqdori: <b>5000 so'm</b>"))
            return
    except ValueError:
        await message.reply(error("Miqdor noto'g'ri. Raqam kiriting."))
        return

    await state.update_data(amount_local=amount)
    await message.reply(
        card(
            "Miqdor Qabul Qilindi",
            [
                f"Admin aloqa: <b>{get_admin_contact_text()}</b>",
                "Iltimos, admin bilan aloqaga chiqing.",
            ],
        )
    )

    contact_markup = get_admin_contact_markup()
    if contact_markup:
        await message.reply(card("Admin Aloqa", ["Quyidagi tugma orqali yozing."]), reply_markup=contact_markup)

    await message.reply(card("Izoh Yuborish", ["To'lov haqida izoh yoki chek ma'lumotini yuboring."]))
    await state.set_state(TopupStates.waiting_for_note)


@router.message(TopupStates.waiting_for_note)
async def topup_note(message: Message, state: FSMContext, db: AsyncSession):
    if message.text in MAIN_MENU_BUTTONS:
        await state.clear()
        await message.reply(card("Hisobni To'ldirish", ["Jarayon bekor qilindi."]), reply_markup=get_main_menu())
        return

    data = await state.get_data()
    amount_local = float(data["amount_local"])
    method = data.get("payment_method", "cash")
    note = message.text.strip() if message.text else None

    user = await validate_user_access(db, message.from_user.id)
    req = await create_topup_request(db, user.id, amount_local, payment_method=method, payment_note=note)

    rate_100 = await get_setting_float(db, "stars_rate_100", 25000.0)
    est_stars = amount_local if method == "stars" else _cash_to_stars(amount_local, rate_100)
    method_text = "Stars" if method == "stars" else "Naxt"
    amount_text = f"{amount_local:.2f} stars" if method == "stars" else f"{amount_local:,.0f} so'm"

    await message.reply(
        card(
            "Topup So'rovi Yuborildi",
            [
                f"So'rov ID: <b>{req.id}</b>",
                f"Turi: <b>{method_text}</b>",
                f"Miqdor: <b>{amount_text}</b>",
                f"Balansga tushishi: <b>{est_stars:.2f} stars</b>",
                "Admin tasdiqlagach balansga qo'shiladi.",
                f"Aloqa: <b>{get_admin_contact_text()}</b>",
            ],
            success("So'rov muvaffaqiyatli qabul qilindi."),
        ),
        reply_markup=get_main_menu(),
    )

    contact_markup = get_admin_contact_markup()
    if contact_markup:
        await message.reply(card("Admin Aloqa", ["Savol bo'lsa bog'laning."]), reply_markup=contact_markup)

    await state.clear()
