from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import (
    check_task_completed,
    claim_task_for_completion,
    create_task_skip_event,
    get_active_tasks,
    get_oldest_user_task_skip_since,
    get_order_by_id,
    get_setting_float,
    get_user_completed_channel_keys,
    get_user_task_skip_count_since,
    get_user_task_completion_count_since,
    get_task_by_id,
    has_user_completed_channel,
    mark_task_completed,
    reactivate_task,
    task_channel_key,
)
from services.order_progress_service import notify_order_progress_update
from utils.reward_system import add_task_reward
from utils.subscription_checker import check_subscription


class TaskService:
    HOURLY_TASK_LIMIT = 10
    DEFAULT_SKIP_LIMIT = 10
    DEFAULT_SKIP_WINDOW_MINUTES = 60

    def __init__(self, db: AsyncSession, bot: Bot):
        self.db = db
        self.bot = bot

    async def is_hourly_limit_reached(self, user_id: int) -> bool:
        since = datetime.utcnow() - timedelta(hours=1)
        count = await get_user_task_completion_count_since(self.db, user_id, since)
        return count >= self.HOURLY_TASK_LIMIT

    async def _get_skip_limit(self) -> int:
        value = await get_setting_float(self.db, "task_skip_limit", float(self.DEFAULT_SKIP_LIMIT))
        return max(1, int(value))

    async def _get_skip_window_minutes(self) -> int:
        value = await get_setting_float(self.db, "task_skip_window_minutes", float(self.DEFAULT_SKIP_WINDOW_MINUTES))
        return max(1, int(value))

    async def get_skip_block_status(self, user_id: int) -> dict:
        limit = await self._get_skip_limit()
        window_minutes = await self._get_skip_window_minutes()
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        count = await get_user_task_skip_count_since(self.db, user_id, since)
        if count < limit:
            return {"blocked": False, "remaining_seconds": 0, "count": count, "limit": limit}

        oldest = await get_oldest_user_task_skip_since(self.db, user_id, since)
        if not oldest:
            return {"blocked": False, "remaining_seconds": 0, "count": count, "limit": limit}

        unblock_at = oldest + timedelta(minutes=window_minutes)
        remaining_seconds = max(0, int((unblock_at - datetime.utcnow()).total_seconds()))
        return {"blocked": True, "remaining_seconds": remaining_seconds, "count": count, "limit": limit}

    async def register_skip(self, user_id: int) -> dict:
        await create_task_skip_event(self.db, user_id)
        return await self.get_skip_block_status(user_id)

    async def get_next_task(self, user_id: int):
        current_reward = await get_setting_float(self.db, "task_reward", 0.30)
        tasks = await get_active_tasks(self.db)
        completed_channels = await get_user_completed_channel_keys(self.db, user_id)
        for task in tasks:
            if task_channel_key(task.channel_username) in completed_channels:
                continue
            if not await check_task_completed(self.db, user_id, task.id):
                task.reward = current_reward
                return task
        return None

    async def complete_task(self, user_id: int, telegram_id: int, task_id: int) -> bool:
        if await self.is_hourly_limit_reached(user_id):
            return False

        if await check_task_completed(self.db, user_id, task_id):
            return False

        task = await get_task_by_id(self.db, task_id)
        if not task or not task.active:
            return False
        if await has_user_completed_channel(self.db, user_id, task.channel_username):
            return False

        if not await check_subscription(self.bot, telegram_id, task.channel_username):
            return False

        claimed = await claim_task_for_completion(self.db, task_id)
        if not claimed:
            return False

        order_owner_id = None
        if task.order_id:
            order = await get_order_by_id(self.db, task.order_id)
            order_owner_id = order.user_id if order else None

        reward = await get_setting_float(self.db, "task_reward", 0.30)
        is_marked = await mark_task_completed(self.db, user_id, task_id, order_owner_user_id=order_owner_id)
        if not is_marked:
            await reactivate_task(self.db, task_id)
            return False
        await add_task_reward(self.db, user_id, reward)
        await notify_order_progress_update(
            bot=self.bot,
            db=self.db,
            order_id=task.order_id,
            order_owner_id=order_owner_id,
            delta=1,
        )
        return True
