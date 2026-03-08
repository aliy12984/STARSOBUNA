from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import create_transaction, get_user_balance, update_referral_commission, update_user_balance


async def add_task_reward(db: AsyncSession, user_id: int, task_reward: float):
    await update_user_balance(db, user_id, task_reward)
    await create_transaction(db, user_id, "task_reward", task_reward, f"Task reward: {task_reward:.2f} stars")


async def add_referral_commission(db: AsyncSession, referrer_id: int, commission: float):
    await update_user_balance(db, referrer_id, commission)
    await create_transaction(db, referrer_id, "referral_reward", commission, f"Referral reward: {commission:.2f} stars")
    await update_referral_commission(db, referrer_id, commission)


async def add_daily_bonus(db: AsyncSession, user_id: int, bonus: float):
    await update_user_balance(db, user_id, bonus)
    await create_transaction(db, user_id, "daily_bonus", bonus, f"Daily bonus: {bonus:.2f} stars")


async def deduct_order_payment(db: AsyncSession, user_id: int, amount: float, description: str):
    await update_user_balance(db, user_id, -amount)
    await create_transaction(db, user_id, "order_payment", -amount, description)


async def apply_unsubscribe_penalty(
    db: AsyncSession,
    worker_user_id: int,
    order_owner_user_id: int,
    worker_penalty: float,
    owner_reward: float,
):
    current_balance = await get_user_balance(db, worker_user_id)
    deducted = min(worker_penalty, current_balance)
    if deducted > 0:
        await update_user_balance(db, worker_user_id, -deducted)
        await create_transaction(
            db,
            worker_user_id,
            "unsubscribe_penalty",
            -deducted,
            f"Left channel before 15 days: -{deducted:.2f} stars",
        )

    if order_owner_user_id:
        await update_user_balance(db, order_owner_user_id, owner_reward)
        await create_transaction(
            db,
            order_owner_user_id,
            "unsubscribe_compensation",
            owner_reward,
            f"Compensation from unsubscribe: +{owner_reward:.2f} stars",
        )
