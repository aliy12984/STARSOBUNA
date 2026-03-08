from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import (
    create_task,
    format_channel_ref_for_view,
    get_active_mandatory_channels,
    get_recent_completed_tasks_for_user,
    get_setting_float,
    mark_unsubscribe_penalty_applied,
)
from services.order_progress_service import notify_order_progress_update
from utils.reward_system import apply_unsubscribe_penalty


def normalize_channel(channel_username: str) -> str:
    return channel_username.strip()


def resolve_chat_target(channel_ref: str):
    value = normalize_channel(channel_ref)
    if value.startswith("@"):
        return value
    if value.lstrip("-").isdigit():
        return int(value)
    if value.startswith("http://t.me/") or value.startswith("https://t.me/"):
        tail = value.split("t.me/", 1)[1].strip("/")
        tail = tail.split("?", 1)[0]
        if tail.startswith("+"):
            return None
        if tail:
            return f"@{tail.lstrip('@')}"
    return f"@{value.lstrip('@')}"


async def check_subscription(bot: Bot, user_id: int, channel_username: str) -> bool:
    try:
        chat_target = resolve_chat_target(channel_username)
        if chat_target is None:
            return False
        chat_member = await bot.get_chat_member(chat_target, user_id)
        return chat_member.status in ["member", "administrator", "creator", "restricted"]
    except TelegramBadRequest:
        return False
    except Exception:
        return False


async def get_unsubscribed_mandatory_channels(db: AsyncSession, bot: Bot, user_id: int):
    channels = await get_active_mandatory_channels(db)
    missing = []
    for channel in channels:
        is_subscribed = await check_subscription(bot, user_id, channel.channel_username)
        if not is_subscribed:
            missing.append(
                {
                    "channel_ref": channel.channel_username,
                    "display": format_channel_ref_for_view(channel.channel_username),
                    "join_link": channel.join_link,
                }
            )
    return missing


async def process_unsubscribe_penalties(
    db: AsyncSession,
    bot: Bot,
    worker_db_user_id: int,
    worker_telegram_id: int,
):
    completed = await get_recent_completed_tasks_for_user(db, worker_db_user_id, within_days=15)
    if not completed:
        return 0

    worker_penalty = await get_setting_float(db, "unsubscribe_penalty_worker", 0.10)
    owner_reward = await get_setting_float(db, "unsubscribe_reward_order_owner", 0.05)
    applied = 0
    progress_changes: dict[tuple[int, int], int] = {}

    for completed_task, task in completed:
        still_subscribed = await check_subscription(bot, worker_telegram_id, task.channel_username)
        if still_subscribed:
            continue

        await apply_unsubscribe_penalty(
            db,
            worker_user_id=worker_db_user_id,
            order_owner_user_id=completed_task.order_owner_user_id,
            worker_penalty=worker_penalty,
            owner_reward=owner_reward,
        )
        await mark_unsubscribe_penalty_applied(db, completed_task.id)
        # Put this channel back to the task queue so another worker can join.
        await create_task(db, task.channel_username, task.reward, order_id=task.order_id)
        if task.order_id and completed_task.order_owner_user_id:
            key = (int(task.order_id), int(completed_task.order_owner_user_id))
            progress_changes[key] = progress_changes.get(key, 0) - 1
        applied += 1

    for (order_id, owner_id), delta in progress_changes.items():
        await notify_order_progress_update(
            bot=bot,
            db=db,
            order_id=order_id,
            order_owner_id=owner_id,
            delta=delta,
        )

    return applied
