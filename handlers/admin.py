from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.queries import (
    add_mandatory_channel,
    create_task,
    create_transaction,
    deactivate_mandatory_channel,
    get_all_users,
    get_channels_overview,
    get_pending_topup_requests,
    get_pending_withdraws,
    get_setting_float,
    get_topup_request_by_id,
    get_total_stats,
    get_user_balance,
    get_user_by_id,
    get_user_by_telegram_id,
    set_setting,
    update_topup_request_status,
    update_user_balance,
    update_user_banned,
)
from keyboards.admin_menu import (
    BTN_ADMIN_ADD_BALANCE,
    BTN_ADMIN_ADD_BALANCE_LONG,
    BTN_ADMIN_ADD_BALANCE_OLD,
    BTN_ADMIN_ADD_MANDATORY,
    BTN_ADMIN_ADD_TASK_CHANNEL,
    BTN_ADMIN_BAN,
    BTN_ADMIN_BROADCAST,
    BTN_ADMIN_CHANNELS,
    BTN_ADMIN_REMOVE_MANDATORY,
    BTN_ADMIN_SET_RATE,
    BTN_ADMIN_SET_CONTACT,
    BTN_ADMIN_SET_REF,
    BTN_ADMIN_SET_SKIP_LIMIT,
    BTN_ADMIN_SET_SKIP_WINDOW,
    BTN_ADMIN_SET_TASK_REWARD,
    BTN_ADMIN_STATS,
    BTN_ADMIN_SUB_BALANCE,
    BTN_ADMIN_SUB_BALANCE_OLD,
    BTN_ADMIN_TOPUP_REQUESTS,
    BTN_ADMIN_WITHDRAWS,
    BTN_ADMIN_WITHDRAWS_OLD,
    get_admin_menu,
)
from keyboards.menu import BTN_MAIN_MENU, MAIN_MENU_BUTTONS, get_main_menu
from utils.ui import card, error, info, success, warning

router = Router()


class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_ban_user = State()
    waiting_for_add_balance = State()
    waiting_for_sub_balance = State()
    waiting_for_task_channel = State()
    waiting_for_mandatory_channel = State()
    waiting_for_remove_mandatory_channel = State()
    waiting_for_referral_reward = State()
    waiting_for_task_reward = State()
    waiting_for_skip_limit = State()
    waiting_for_skip_window = State()
    waiting_for_deposit_rate = State()
    waiting_for_admin_contact = State()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


ADMIN_MENU_BUTTONS = [
    BTN_ADMIN_STATS,
    BTN_ADMIN_BROADCAST,
    BTN_ADMIN_WITHDRAWS,
    BTN_ADMIN_WITHDRAWS_OLD,
    BTN_ADMIN_BAN,
    BTN_ADMIN_ADD_BALANCE,
    BTN_ADMIN_ADD_BALANCE_LONG,
    BTN_ADMIN_ADD_BALANCE_OLD,
    BTN_ADMIN_SUB_BALANCE,
    BTN_ADMIN_SUB_BALANCE_OLD,
    BTN_ADMIN_CHANNELS,
    BTN_ADMIN_ADD_TASK_CHANNEL,
    BTN_ADMIN_ADD_MANDATORY,
    BTN_ADMIN_REMOVE_MANDATORY,
    BTN_ADMIN_SET_REF,
    BTN_ADMIN_SET_TASK_REWARD,
    BTN_ADMIN_SET_SKIP_LIMIT,
    BTN_ADMIN_SET_SKIP_WINDOW,
    BTN_ADMIN_SET_RATE,
    BTN_ADMIN_SET_CONTACT,
    BTN_ADMIN_TOPUP_REQUESTS,
]


async def resolve_target_user(db: AsyncSession, user_ref: str):
    if user_ref.lower().startswith("tg:"):
        try:
            telegram_id = int(user_ref.split(":", 1)[1].strip())
        except ValueError:
            return None
        return await get_user_by_telegram_id(db, telegram_id)

    try:
        numeric_id = int(user_ref.strip())
    except ValueError:
        return None

    user = await get_user_by_id(db, numeric_id)
    if user:
        return user
    return await get_user_by_telegram_id(db, numeric_id)


async def cancel_admin_flow_if_needed(message: Message, state: FSMContext) -> bool:
    text = (message.text or "").strip()
    if not text:
        return False

    if text in MAIN_MENU_BUTTONS:
        await state.clear()
        await message.reply(info("Jarayon bekor qilindi."), reply_markup=get_main_menu())
        return True

    if text.startswith("/") or text in ADMIN_MENU_BUTTONS:
        await state.clear()
        await message.reply(info("Jarayon bekor qilindi. Kerakli bo'limni qayta tanlang."), reply_markup=get_admin_menu())
        return True

    return False


@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply(error("Ruxsat yo'q."))
        return
    await message.reply(
        card(
            "Admin Panel",
            [
                "Kerakli bo'limni tanlang.",
                "Faol jarayonni bekor qilish uchun Asosiy menyu yoki boshqa admin tugmasini bosing.",
            ],
        ),
        reply_markup=get_admin_menu(),
    )


@router.message(F.text == BTN_ADMIN_STATS)
async def admin_stats(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    stats = await get_total_stats(db)
    referral_reward = await get_setting_float(db, "referral_reward", 0.10)
    task_reward = await get_setting_float(db, "task_reward", 0.30)
    skip_limit = int(await get_setting_float(db, "task_skip_limit", 10))
    skip_window = int(await get_setting_float(db, "task_skip_window_minutes", 60))
    stars_rate_100 = await get_setting_float(db, "stars_rate_100", 25000.0)
    text = card(
        "Admin Statistika",
        [
            f"Foydalanuvchilar: <b>{stats['users']}</b>",
            f"Buyurtmalar: <b>{stats['orders']}</b>",
            f"Tasklar: <b>{stats['tasks']}</b>",
            f"Kutilayotgan yechish: <b>{stats['pending_withdraws']}</b>",
            "<code>------------------------------</code>",
            "Sozlamalar:",
            f"Task puli: <b>{task_reward:.2f} stars</b>",
            f"Referral puli: <b>{referral_reward:.2f} stars</b>",
            f"Skip limit: <b>{skip_limit}</b>",
            f"Skip oynasi: <b>{skip_window} daqiqa</b>",
            f"Kurs: <b>100 stars = {stars_rate_100:,.0f} so'm</b>",
        ],
    )
    await message.reply(text, reply_markup=get_admin_menu())


@router.message(F.text == BTN_ADMIN_CHANNELS)
async def channels_overview(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    data = await get_channels_overview(db)
    task_text = "\n".join(data["task_channels"]) if data["task_channels"] else "yo'q"
    if data["mandatory_channels"]:
        mandatory_text = "\n".join(
            f"{item['channel']} | link: {item['join_link']}" for item in data["mandatory_channels"]
        )
    else:
        mandatory_text = "yo'q"
    await message.reply(
        card(
            "Kanal Ro'yxati",
            [
                "Task kanallar:",
                task_text,
                "<code>------------------------------</code>",
                "Majburiy kanallar:",
                mandatory_text,
            ],
        ),
        reply_markup=get_admin_menu(),
    )


@router.message(F.text == BTN_ADMIN_ADD_TASK_CHANNEL)
async def add_task_channel_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply(
        card(
            "Task Kanal Qo'shish",
            [
                "Format: <code>@kanal soni</code>",
                "Masalan: <code>@mychannel 20</code>",
            ],
        )
    )
    await state.set_state(AdminStates.waiting_for_task_channel)


@router.message(AdminStates.waiting_for_task_channel)
async def add_task_channel_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return

    try:
        channel, count_raw = (message.text or "").split(maxsplit=1)
        count = int(count_raw)
        if not channel.startswith("@") or count <= 0:
            raise ValueError
    except ValueError:
        await message.reply(error("Noto'g'ri format. Masalan: @mychannel 20"))
        return

    task_reward = await get_setting_float(db, "task_reward", 0.30)
    normalized_channel = channel.strip().lstrip("@")
    for _ in range(count):
        await create_task(db, normalized_channel, task_reward)
    await message.reply(success(f"{count} ta task qo'shildi: @{normalized_channel}"), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_ADD_MANDATORY)
async def add_mandatory_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply(
        card(
            "Majburiy Kanal Qo'shish",
            [
                "Format: <code>kanal_ref [join_link]</code>",
                "Public: <code>@mychannel</code>",
                "Private: <code>-1001234567890 https://t.me/+AbCdEf</code>",
            ],
        )
    )
    await state.set_state(AdminStates.waiting_for_mandatory_channel)


@router.message(AdminStates.waiting_for_mandatory_channel)
async def add_mandatory_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return

    raw = (message.text or "").strip()
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|", 1)]
    else:
        parts = raw.split(maxsplit=1)

    if not parts:
        await message.reply(error("Kanal ma'lumoti yuboring."))
        return

    channel_ref = parts[0]
    join_link = parts[1].strip() if len(parts) > 1 else None

    is_channel_ref_valid = (
        channel_ref.startswith("@")
        or channel_ref.lstrip("-").isdigit()
        or channel_ref.startswith("https://t.me/")
        or channel_ref.startswith("http://t.me/")
    )
    if not is_channel_ref_valid:
        await message.reply(error("kanal_ref noto'g'ri. @username yoki -100... yuboring."))
        return
    if (channel_ref.startswith("https://t.me/+") or channel_ref.startswith("http://t.me/+")) and not channel_ref.lstrip("-").isdigit():
        await message.reply(error("Private kanal uchun kanal_ref sifatida -100... chat ID kiriting, join-link ni alohida yuboring."))
        return

    if join_link and not (join_link.startswith("https://t.me/") or join_link.startswith("http://t.me/")):
        await message.reply(error("join_link noto'g'ri. https://t.me/... bo'lsin."))
        return

    await add_mandatory_channel(db, channel_ref, join_link)
    response = success("Majburiy kanal qo'shildi.")
    if join_link:
        response += f"\nJoin-link: <code>{join_link}</code>"
    await message.reply(response, reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_REMOVE_MANDATORY)
async def remove_mandatory_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply(
        card(
            "Majburiy Kanal O'chirish",
            ["Kanal_ref kiriting: <code>@username</code> yoki <code>-100...</code>"],
        )
    )
    await state.set_state(AdminStates.waiting_for_remove_mandatory_channel)


@router.message(AdminStates.waiting_for_remove_mandatory_channel)
async def remove_mandatory_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    await deactivate_mandatory_channel(db, message.text or "")
    await message.reply(success("Majburiy kanal o'chirildi."), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_SET_REF)
async def set_referral_reward_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply("Yangi referral pulini yuboring.\nMasalan: <code>0.15</code>")
    await state.set_state(AdminStates.waiting_for_referral_reward)


@router.message(AdminStates.waiting_for_referral_reward)
async def set_referral_reward_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    try:
        amount = float((message.text or "").strip())
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.reply(error("Miqdor noto'g'ri."))
        return
    await set_setting(db, "referral_reward", str(amount))
    await message.reply(success(f"Referral puli yangilandi: {amount:.2f} stars"), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_SET_TASK_REWARD)
async def set_task_reward_start(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    current = await get_setting_float(db, "task_reward", 0.30)
    await message.reply(
        f"Joriy task puli: <b>{current:.2f} stars</b>\n"
        "Yangi qiymat kiriting. Masalan: <code>0.30</code>"
    )
    await state.set_state(AdminStates.waiting_for_task_reward)


@router.message(AdminStates.waiting_for_task_reward)
async def set_task_reward_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    try:
        amount = float((message.text or "").strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply(error("Qiymat noto'g'ri. Masalan: <code>0.30</code>"))
        return
    await set_setting(db, "task_reward", str(amount))
    await message.reply(success(f"Task puli yangilandi: {amount:.2f} stars"), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_SET_SKIP_LIMIT)
async def set_skip_limit_start(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    current = int(await get_setting_float(db, "task_skip_limit", 10))
    await message.reply(
        f"Joriy skip limit: <b>{current}</b>\n"
        "Yangi limit kiriting. Masalan: <code>10</code>"
    )
    await state.set_state(AdminStates.waiting_for_skip_limit)


@router.message(AdminStates.waiting_for_skip_limit)
async def set_skip_limit_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    try:
        limit = int((message.text or "").strip())
        if limit <= 0:
            raise ValueError
    except ValueError:
        await message.reply(error("Limit noto'g'ri. Masalan: <code>10</code>"))
        return
    await set_setting(db, "task_skip_limit", str(limit))
    await message.reply(success(f"Skip limit yangilandi: {limit}"), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_SET_SKIP_WINDOW)
async def set_skip_window_start(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    current = int(await get_setting_float(db, "task_skip_window_minutes", 60))
    await message.reply(
        f"Joriy skip oynasi: <b>{current} daqiqa</b>\n"
        "Yangi daqiqa kiriting. Masalan: <code>60</code>"
    )
    await state.set_state(AdminStates.waiting_for_skip_window)


@router.message(AdminStates.waiting_for_skip_window)
async def set_skip_window_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    try:
        minutes = int((message.text or "").strip())
        if minutes <= 0:
            raise ValueError
    except ValueError:
        await message.reply(error("Daqiqa noto'g'ri. Masalan: <code>60</code>"))
        return
    await set_setting(db, "task_skip_window_minutes", str(minutes))
    await message.reply(success(f"Skip oynasi yangilandi: {minutes} daqiqa"), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_SET_RATE)
async def set_deposit_rate_start(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    current_rate = await get_setting_float(db, "stars_rate_100", 25000.0)
    await message.reply(
        f"Joriy kurs: <b>100 stars = {current_rate:,.0f} so'm</b>\n"
        "Yangi kursni kiriting (masalan: <code>25000</code>)."
    )
    await state.set_state(AdminStates.waiting_for_deposit_rate)


@router.message(AdminStates.waiting_for_deposit_rate)
async def set_deposit_rate_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    try:
        rate = float((message.text or "").replace(",", "").strip())
        if rate <= 0:
            raise ValueError
    except ValueError:
        await message.reply(error("Kurs noto'g'ri. Masalan: <code>25000</code>"))
        return

    await set_setting(db, "stars_rate_100", str(rate))
    await set_setting(db, "deposit_rate", str(rate))
    await message.reply(success(f"Kurs yangilandi: 100 stars = {rate:,.0f} so'm"), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_SET_CONTACT)
async def set_admin_contact_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    current = (config.ADMIN_CONTACT or "").strip() or "o'rnatilmagan"
    await message.reply(
        "Admin aloqasini yuboring.\n"
        "Qabul qilinadi: <code>@username</code>, <code>https://t.me/...</code>, <code>t.me/...</code>, yoki <code>telegram_id</code>\n"
        f"Joriy qiymat: <b>{current}</b>"
    )
    await state.set_state(AdminStates.waiting_for_admin_contact)


@router.message(AdminStates.waiting_for_admin_contact)
async def set_admin_contact_process(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return

    value = (message.text or "").strip()
    is_valid = (
        value.startswith("@")
        or value.startswith("https://t.me/")
        or value.startswith("http://t.me/")
        or value.startswith("t.me/")
        or value.isdigit()
    )
    if not is_valid:
        await message.reply(error("Noto'g'ri format. Masalan: <code>@your_admin</code>"))
        return

    await set_setting(db, "admin_contact", value)
    config.ADMIN_CONTACT = value
    await message.reply(success(f"Admin aloqasi yangilandi: <b>{value}</b>"), reply_markup=get_admin_menu())
    await state.clear()


@router.message(F.text == BTN_ADMIN_TOPUP_REQUESTS)
async def topup_requests_list(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    pending = await get_pending_topup_requests(db)
    if not pending:
        await message.reply(card("Topup So'rovlari", ["Kutilayotgan to'ldirish so'rovlari yo'q."]), reply_markup=get_admin_menu())
        return

    rate = await get_setting_float(db, "stars_rate_100", 25000.0)
    lines = [f"Kurs: <b>100 stars = {rate:,.0f} so'm</b>"]
    for req in pending[:20]:
        method = (req.payment_method or "cash").lower()
        if method == "stars":
            stars_amount = float(req.amount_local or 0.0)
            method_label = "Stars"
            amount_label = f"{stars_amount:.2f} stars"
        else:
            stars_amount = round((float(req.amount_local or 0.0) * 100.0 / rate), 2) if rate > 0 else 0.0
            method_label = "Naxt"
            amount_label = f"{float(req.amount_local or 0.0):,.0f} so'm"
        note = (req.payment_note or "-").strip()
        if len(note) > 60:
            note = note[:57] + "..."
        lines.append(
            (
                f"ID: <b>{req.id}</b> | User: <b>{req.user_id}</b>\n"
                f"Turi: <b>{method_label}</b>\n"
                f"Summa: <b>{amount_label}</b>\n"
                f"Balansga: <b>{stars_amount:.2f} stars</b>\n"
                f"Izoh: <code>{note}</code>\n"
                "<code>------------------------------</code>"
            )
        )
    await message.reply(
        card(
            "To'ldirish So'rovlari",
            lines,
            "Tasdiqlash: /approvetopup ID | Rad etish: /rejecttopup ID",
        ),
        reply_markup=get_admin_menu(),
    )


@router.message(F.text == BTN_ADMIN_BROADCAST)
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply(card("Broadcast", ["Yuboriladigan xabar matnini yuboring."]))
    await state.set_state(AdminStates.waiting_for_broadcast)


@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, db: AsyncSession, bot):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    body = message.html_text or message.text
    if not body:
        await message.reply(error("Xabar matni bo'sh bo'lmasligi kerak."))
        return

    users = await get_all_users(db)
    sent_count = 0
    failed_count = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, body)
            sent_count += 1
        except Exception:
            failed_count += 1

    await message.reply(
        success("Broadcast yakunlandi.")
        + "\n"
        + f"Yuborildi: <b>{sent_count}</b>\n"
        + f"Xatolik: <b>{failed_count}</b>",
        reply_markup=get_admin_menu(),
    )
    await state.clear()


@router.message(F.text.in_([BTN_ADMIN_WITHDRAWS, BTN_ADMIN_WITHDRAWS_OLD]))
async def withdraw_requests(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    withdraws = await get_pending_withdraws(db)
    if not withdraws:
        await message.reply(card("Yechish So'rovlari", ["Kutilayotgan so'rov yo'q."]), reply_markup=get_admin_menu())
        return
    lines = []
    for w in withdraws[:15]:
        lines.append(
            (
                f"ID: <b>{w.id}</b> | User: <b>{w.user_id}</b>\n"
                f"Amount: <b>{w.amount:.2f} stars</b>\n"
                f"Wallet: <code>{w.wallet}</code>\n"
                "<code>------------------------------</code>"
            )
        )
    await message.reply(card("Yechish So'rovlari", lines), reply_markup=get_admin_menu())


@router.message(F.text == BTN_ADMIN_BAN)
async def ban_user_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply(card("Ban Qilish", ["Ban qilish uchun ichki user ID kiriting."]))
    await state.set_state(AdminStates.waiting_for_ban_user)


@router.message(AdminStates.waiting_for_ban_user)
async def process_ban(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return
    try:
        user_id = int((message.text or "").strip())
    except ValueError:
        await message.reply(error("User ID noto'g'ri."))
        return

    await update_user_banned(db, user_id, True)
    await message.reply(success(f"User {user_id} ban qilindi."), reply_markup=get_admin_menu())
    await state.clear()


@router.message(Command("approvetopup"))
async def approve_topup_request(message: Message, db: AsyncSession, bot):
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(card("Topup Tasdiqlash", ["Format: <code>/approvetopup ID</code>"]))
        return
    try:
        request_id = int(parts[1].strip())
    except ValueError:
        await message.reply(error("ID noto'g'ri."))
        return

    req = await get_topup_request_by_id(db, request_id)
    if not req:
        await message.reply(error("So'rov topilmadi."))
        return
    if req.status != "pending":
        await message.reply(info(f"Bu so'rov allaqachon <b>{req.status}</b> holatda."))
        return

    method = (req.payment_method or "cash").lower()
    rate = await get_setting_float(db, "stars_rate_100", 25000.0)
    if rate <= 0:
        await message.reply(error("Kurs noto'g'ri. Avval kursni sozlang."))
        return

    if method == "stars":
        stars_amount = round(float(req.amount_local or 0.0), 2)
        source_text = f"stars={stars_amount:.2f}"
    else:
        stars_amount = round((float(req.amount_local or 0.0) * 100.0 / rate), 2)
        source_text = f"cash={float(req.amount_local or 0.0):.2f} so'm, rate100={rate:.2f}"

    await update_user_balance(db, req.user_id, stars_amount)
    await create_transaction(
        db,
        req.user_id,
        "topup_approved",
        stars_amount,
        f"Topup approved by admin {message.from_user.id}: {source_text}, +{stars_amount:.2f} stars",
    )
    await update_topup_request_status(db, req.id, "approved", usd_amount=stars_amount)
    await message.reply(
        success("To'ldirish so'rovi tasdiqlandi.")
        + "\n"
        + f"ID: <b>{req.id}</b>\n"
        + f"User: <b>{req.user_id}</b>\n"
        + f"Balansga tushdi: <b>{stars_amount:.2f} stars</b>",
        reply_markup=get_admin_menu(),
    )
    target_user = await get_user_by_id(db, req.user_id)
    if target_user:
        try:
            await bot.send_message(
                target_user.telegram_id,
                success(
                    "To'ldirish so'rovingiz tasdiqlandi.\n"
                    f"Balansga qo'shildi: <b>{stars_amount:.2f} stars</b>"
                ),
            )
        except Exception:
            pass


@router.message(Command("rejecttopup"))
async def reject_topup_request(message: Message, db: AsyncSession, bot):
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(card("Topup Rad Etish", ["Format: <code>/rejecttopup ID</code>"]))
        return
    try:
        request_id = int(parts[1].strip())
    except ValueError:
        await message.reply(error("ID noto'g'ri."))
        return

    req = await get_topup_request_by_id(db, request_id)
    if not req:
        await message.reply(error("So'rov topilmadi."))
        return
    if req.status != "pending":
        await message.reply(info(f"Bu so'rov allaqachon <b>{req.status}</b> holatda."))
        return

    await update_topup_request_status(db, req.id, "rejected")
    await message.reply(info(f"So'rov rad etildi. ID: <b>{req.id}</b>"), reply_markup=get_admin_menu())
    target_user = await get_user_by_id(db, req.user_id)
    if target_user:
        try:
            await bot.send_message(
                target_user.telegram_id,
                warning("To'ldirish so'rovingiz rad etildi.\nIltimos, admin bilan bog'laning yoki qayta yuboring."),
            )
        except Exception:
            pass


@router.message(Command("addbalance"))
@router.message(F.text.in_([BTN_ADMIN_ADD_BALANCE, BTN_ADMIN_ADD_BALANCE_LONG, BTN_ADMIN_ADD_BALANCE_OLD]))
async def add_balance_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply(
        card(
            "Balans Qo'shish",
            [
                "Format: <code>id miqdor</code>",
                "ID quyidagilardan biri bo'lishi mumkin:",
                "- Ichki user ID: <code>1</code>",
                "- Telegram ID: <code>123456789</code>",
                "- Yoki aniq: <code>tg:123456789</code>",
                "Misol: <code>tg:123456789 25</code>",
            ],
        )
    )
    await state.set_state(AdminStates.waiting_for_add_balance)
    return
    await message.reply(
        "Format: <code>id miqdor</code>\n"
        "ID quyidagilardan biri bo'lishi mumkin:\n"
        "• Ichki user ID: <code>1</code>\n"
        "• Telegram ID: <code>123456789</code>\n"
        "• Yoki aniq: <code>tg:123456789</code>\n\n"
        "Misol: <code>tg:123456789 25</code>"
    )
    await state.set_state(AdminStates.waiting_for_add_balance)


@router.message(AdminStates.waiting_for_add_balance)
async def process_add_balance(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return

    try:
        user_ref, amount_str = (message.text or "").split(maxsplit=1)
        amount = float(amount_str)
    except ValueError:
        await message.reply(error("Format noto'g'ri."))
        return

    if amount <= 0:
        await message.reply(error("Miqdor 0 dan katta bo'lishi kerak."))
        return

    target_user = await resolve_target_user(db, user_ref)
    if not target_user:
        await message.reply(error("Foydalanuvchi topilmadi."))
        return

    await update_user_balance(db, target_user.id, amount)
    await create_transaction(
        db,
        target_user.id,
        "admin_adjustment",
        amount,
        f"Admin {message.from_user.id} added {amount:.2f} stars",
    )
    await message.reply(
        success("Balans muvaffaqiyatli qo'shildi.")
        + "\n"
        + f"User ID: <b>{target_user.id}</b>\n"
        + f"Telegram ID: <b>{target_user.telegram_id}</b>\n"
        + f"Miqdor: <b>{amount:.2f} stars</b>",
        reply_markup=get_admin_menu(),
    )
    await state.clear()


@router.message(Command("subbalance"))
@router.message(F.text.in_([BTN_ADMIN_SUB_BALANCE, BTN_ADMIN_SUB_BALANCE_OLD]))
async def sub_balance_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.reply(
        card(
            "Balans Ayirish",
            [
                "Format: <code>id miqdor</code>",
                "ID quyidagilardan biri bo'lishi mumkin:",
                "- Ichki user ID: <code>1</code>",
                "- Telegram ID: <code>123456789</code>",
                "- Yoki aniq: <code>tg:123456789</code>",
                "Misol: <code>tg:123456789 10</code>",
            ],
        )
    )
    await state.set_state(AdminStates.waiting_for_sub_balance)
    return
    await message.reply(
        "Format: <code>id miqdor</code>\n"
        "ID quyidagilardan biri bo'lishi mumkin:\n"
        "• Ichki user ID: <code>1</code>\n"
        "• Telegram ID: <code>123456789</code>\n"
        "• Yoki aniq: <code>tg:123456789</code>\n\n"
        "Misol: <code>tg:123456789 10</code>"
    )
    await state.set_state(AdminStates.waiting_for_sub_balance)


@router.message(AdminStates.waiting_for_sub_balance)
async def process_sub_balance(message: Message, state: FSMContext, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return
    if await cancel_admin_flow_if_needed(message, state):
        return

    try:
        user_ref, amount_str = (message.text or "").split(maxsplit=1)
        amount = float(amount_str)
    except ValueError:
        await message.reply(error("Format noto'g'ri."))
        return

    if amount <= 0:
        await message.reply(error("Miqdor 0 dan katta bo'lishi kerak."))
        return

    target_user = await resolve_target_user(db, user_ref)
    if not target_user:
        await message.reply(error("Foydalanuvchi topilmadi."))
        return

    current_balance = await get_user_balance(db, target_user.id)
    if current_balance < amount:
        await message.reply(
            warning(f"Balans yetarli emas.\nJoriy balans: <b>{current_balance:.2f} stars</b>"),
            reply_markup=get_admin_menu(),
        )
        await state.clear()
        return

    await update_user_balance(db, target_user.id, -amount)
    await create_transaction(
        db,
        target_user.id,
        "admin_adjustment",
        -amount,
        f"Admin {message.from_user.id} deducted {amount:.2f} stars",
    )
    await message.reply(
        success("Balansdan ayirildi.")
        + "\n"
        + f"User ID: <b>{target_user.id}</b>\n"
        + f"Telegram ID: <b>{target_user.telegram_id}</b>\n"
        + f"Miqdor: <b>-{amount:.2f} stars</b>",
        reply_markup=get_admin_menu(),
    )
    await state.clear()
