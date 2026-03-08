from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import (
    create_order,
    create_task,
    create_transaction,
    deactivate_active_tasks_for_order,
    get_active_orders_by_user,
    get_order_last_completion_at,
    get_order_progress,
    get_setting_float,
    get_user_balance,
    set_order_status,
    update_user_balance,
)
from utils.reward_system import deduct_order_payment


class OrderService:
    def __init__(self, db: AsyncSession, bot: Bot):
        self.db = db
        self.bot = bot

    async def check_bot_admin(self, channel_username: str) -> bool:
        try:
            username = channel_username.strip().lstrip("@")
            chat_member = await self.bot.get_chat_member(f"@{username}", self.bot.id)
            return chat_member.status in ["administrator", "creator"]
        except Exception:
            return False

    async def create_order(self, user_id: int, channel_username: str, subscribers_needed: int) -> dict:
        if not await self.check_bot_admin(channel_username):
            raise ValueError("Bot bu kanalda admin emas.")

        if subscribers_needed < 20:
            raise ValueError("Minimal obunachi soni 20 ta bo'lishi kerak.")

        subscriber_price = await get_setting_float(self.db, "subscriber_price", 0.30)
        task_reward = await get_setting_float(self.db, "task_reward", 0.30)
        price = subscribers_needed * subscriber_price

        balance = await get_user_balance(self.db, user_id)
        if balance < 15.0:
            raise ValueError("Buyurtma berish uchun balansda kamida 15 stars bo'lishi kerak.")
        if balance < price:
            raise ValueError(f"Balans yetarli emas. Kerak: {price:.2f} stars")

        normalized_channel = channel_username.strip().lstrip("@")
        await deduct_order_payment(
            self.db,
            user_id,
            price,
            f"Order: {subscribers_needed} subscribers for @{normalized_channel}",
        )

        order = await create_order(self.db, user_id, normalized_channel, subscribers_needed, price)
        for _ in range(subscribers_needed):
            await create_task(self.db, normalized_channel, task_reward, order_id=order.id)

        return {"order_id": order.id, "price": price, "subscribers": subscribers_needed}

    async def process_auto_refunds_for_user(self, user_id: int):
        refund_hours = max(1, int(await get_setting_float(self.db, "order_auto_refund_hours", 24.0)))
        refund_ratio = await get_setting_float(self.db, "order_auto_refund_ratio", 0.50)
        refund_ratio = min(max(refund_ratio, 0.0), 1.0)
        subscriber_price = await get_setting_float(self.db, "subscriber_price", 0.30)

        cutoff = datetime.utcnow() - timedelta(hours=refund_hours)
        active_orders = await get_active_orders_by_user(self.db, user_id)
        refunded_orders = []

        for order in active_orders:
            last_completion = await get_order_last_completion_at(self.db, order.id)
            last_activity = last_completion or order.created_at or datetime.utcnow()
            if last_activity > cutoff:
                continue

            progress = await get_order_progress(self.db, order.id)
            if not progress:
                continue
            remaining = int(progress["remaining"])
            if remaining <= 0:
                continue

            refund_amount = round(remaining * subscriber_price * refund_ratio, 2)
            await deactivate_active_tasks_for_order(self.db, order.id)
            await set_order_status(self.db, order.id, "refunded")

            if refund_amount > 0:
                await update_user_balance(self.db, user_id, refund_amount)
                await create_transaction(
                    self.db,
                    user_id,
                    "order_auto_refund",
                    refund_amount,
                    (
                        f"Auto-refund for stale order #{order.id}: "
                        f"remaining={remaining}, ratio={refund_ratio:.2f}, +{refund_amount:.2f} stars"
                    ),
                )

            refunded_orders.append(
                {
                    "order_id": order.id,
                    "remaining": remaining,
                    "refund_amount": refund_amount,
                    "ratio": refund_ratio,
                    "inactive_hours": refund_hours,
                }
            )

        return refunded_orders
