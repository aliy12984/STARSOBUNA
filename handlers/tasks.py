from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.common import enforce_subscription_rules
from keyboards.menu import (
    BTN_CHECK_SUB,
    BTN_EARN,
    BTN_MAIN_MENU,
    BTN_NEXT_TASK,
    get_main_menu,
    get_task_menu,
)
from services.task_service import TaskService
from utils.anti_cheat import validate_user_access
from utils.ui import card, success

router = Router()
TASK_NO_LINK_CB = "task_no_link"


def _task_card_text(task) -> str:
    return card(
        "Vazifa Kartasi",
        [
            f"Kanal: <b>@{task.channel_username.lstrip('@')}</b>",
            f"Mukofot: <b>{task.reward:.2f} stars</b>",
            "Bosqichlar: kanalga kiring, obuna bo'ling, tekshiring.",
        ],
        f"Obuna bo'lgach, <b>{BTN_CHECK_SUB}</b> tugmasini bosing.",
    )


def _task_channel_url(channel_username: str) -> str | None:
    value = (channel_username or "").strip()
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("t.me/"):
        return f"https://{value}"
    if value.lstrip("-").isdigit():
        return None
    return f"https://t.me/{value.lstrip('@')}"


def _task_channel_markup(channel_username: str) -> InlineKeyboardMarkup:
    url = _task_channel_url(channel_username)
    if url:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Kanalga o'tish", url=url)],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Kanal linki yo'q", callback_data=TASK_NO_LINK_CB)],
        ]
    )


async def _send_task_card(message: Message, task):
    await message.reply(_task_card_text(task), reply_markup=get_task_menu())
    await message.reply(
        card("Kanal Havolasi", ["Quyidagi tugma orqali kanalga o'ting."]),
        reply_markup=_task_channel_markup(task.channel_username),
    )


def _format_wait_time(seconds: int) -> str:
    minutes = max(1, (max(0, int(seconds)) + 59) // 60)
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours} soat {mins} daqiqa"
    if hours:
        return f"{hours} soat"
    return f"{mins} daqiqa"


def _skip_block_text(status: dict) -> str:
    wait_text = _format_wait_time(status.get("remaining_seconds", 0))
    limit = status.get("limit", 10)
    return card(
        "Skip Cheklovi",
        [
            "Juda ko'p vazifa skip qilindi.",
            f"Vaqtincha cheklov: <b>{wait_text}</b>",
            f"Limit: 1 soatda <b>{limit}</b> ta skip.",
        ],
        "Vaqt tugagach qayta urinib ko'ring.",
    )


@router.message(F.text == BTN_EARN)
async def earn_money(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return

        user = await validate_user_access(db, message.from_user.id)
        task_service = TaskService(db, bot)
        if await task_service.is_hourly_limit_reached(user.id):
            await message.reply(
                card("Limit Tugadi", ["1 soatlik 10 ta topshiriq limiti tugadi."]),
                reply_markup=get_main_menu(),
            )
            return

        skip_status = await task_service.get_skip_block_status(user.id)
        if skip_status.get("blocked"):
            await message.reply(_skip_block_text(skip_status), reply_markup=get_main_menu())
            return

        task = await task_service.get_next_task(user.id)
        if not task:
            await message.reply(card("Vazifalar", ["Hozircha vazifalar yo'q."]), reply_markup=get_main_menu())
            return

        await _send_task_card(message, task)
    except ValueError as e:
        await message.reply(str(e))


@router.message(F.text == BTN_CHECK_SUB)
async def check_subscription(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return

        user = await validate_user_access(db, message.from_user.id)
        task_service = TaskService(db, bot)
        if await task_service.is_hourly_limit_reached(user.id):
            await message.reply(
                card("Limit Tugadi", ["1 soatda 10 ta topshiriq bajarildi.", "Keyinroq davom eting."]),
                reply_markup=get_main_menu(),
            )
            return

        task = await task_service.get_next_task(user.id)
        if not task:
            await message.reply(card("Vazifalar", ["Barcha vazifalar tugadi."]), reply_markup=get_main_menu())
            return

        is_completed = await task_service.complete_task(user.id, message.from_user.id, task.id)
        if not is_completed:
            await message.reply(
                card(
                    "Tekshirish Natijasi",
                    ["Obuna topilmadi yoki bu vazifa allaqachon bajarilgan."],
                    "Kanalga qayta kirib, keyin tekshirib ko'ring.",
                ),
                reply_markup=get_task_menu(),
            )
            return

        skip_status = await task_service.get_skip_block_status(user.id)
        if skip_status.get("blocked"):
            await message.reply(
                card(
                    "Vazifa Tasdiqlandi",
                    [
                        f"Balansga qo'shildi: <b>+{task.reward:.2f} stars</b>",
                        f"Keyingi vazifa vaqtincha yopildi: <b>{_format_wait_time(skip_status.get('remaining_seconds', 0))}</b>",
                    ],
                    success("Mukofot qo'shildi."),
                ),
                reply_markup=get_main_menu(),
            )
            return

        next_task = await task_service.get_next_task(user.id)
        if not next_task:
            await message.reply(
                card(
                    "Vazifa Tasdiqlandi",
                    [
                        f"Balansga qo'shildi: <b>+{task.reward:.2f} stars</b>",
                        "Barcha vazifalar tugadi.",
                    ],
                    success("Jarayon yakunlandi."),
                ),
                reply_markup=get_main_menu(),
            )
            return

        await message.reply(
            card(
                "Vazifa Tasdiqlandi",
                [
                    f"Balansga qo'shildi: <b>+{task.reward:.2f} stars</b>",
                    "Keyingi vazifa yuborildi.",
                ],
                success("Davom eting."),
            ),
            reply_markup=get_task_menu(),
        )
        await _send_task_card(message, next_task)
    except ValueError as e:
        await message.reply(str(e))


@router.message(F.text == BTN_NEXT_TASK)
async def next_task(message: Message, db: AsyncSession, bot: Bot):
    try:
        if not await enforce_subscription_rules(message, db, bot):
            return

        user = await validate_user_access(db, message.from_user.id)
        task_service = TaskService(db, bot)
        if await task_service.is_hourly_limit_reached(user.id):
            await message.reply(
                card("Limit Tugadi", ["1 soatlik 10 ta topshiriq limiti tugadi."]),
                reply_markup=get_main_menu(),
            )
            return

        skip_status = await task_service.get_skip_block_status(user.id)
        if skip_status.get("blocked"):
            await message.reply(_skip_block_text(skip_status), reply_markup=get_main_menu())
            return

        task = await task_service.get_next_task(user.id)
        if not task:
            await message.reply(card("Vazifalar", ["Barcha vazifalar tugadi."]), reply_markup=get_main_menu())
            return

        skip_status = await task_service.register_skip(user.id)
        if skip_status.get("blocked"):
            await message.reply(_skip_block_text(skip_status), reply_markup=get_main_menu())
            return

        await _send_task_card(message, task)
    except ValueError as e:
        await message.reply(str(e))


@router.message(F.text == BTN_MAIN_MENU)
async def main_menu(message: Message, db: AsyncSession, bot: Bot):
    if not await enforce_subscription_rules(message, db, bot):
        return
    await message.reply(card("Asosiy Menyu", ["Kerakli bo'limni tanlang."]), reply_markup=get_main_menu())


@router.callback_query(F.data == TASK_NO_LINK_CB)
async def task_no_link_callback(callback: CallbackQuery):
    await callback.answer("Bu kanal uchun link topilmadi. Admin bilan bog'laning.", show_alert=True)
