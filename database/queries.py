from datetime import datetime, timedelta
import uuid

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    CompletedTask,
    MandatoryChannel,
    Order,
    Referral,
    SystemSetting,
    Task,
    TaskSkipEvent,
    TopupRequest,
    Transaction,
    User,
    WithdrawRequest,
)


DEFAULT_SETTINGS = {
    "task_reward": "0.30",
    "subscriber_price": "0.30",
    "referral_reward": "0.10",
    "daily_bonus_max": "1.00",
    "unsubscribe_penalty_worker": "0.10",
    "unsubscribe_reward_order_owner": "0.05",
    "task_skip_limit": "10",
    "task_skip_window_minutes": "60",
    "order_auto_refund_hours": "24",
    "order_auto_refund_ratio": "0.50",
    "stars_rate_100": "25000",
    "deposit_rate": "25000",
}


def normalize_channel_ref(value: str) -> str:
    raw = value.strip()
    if raw.startswith("http://t.me/") or raw.startswith("https://t.me/"):
        tail = raw.split("t.me/", 1)[1].strip("/")
        tail = tail.split("?", 1)[0]
        if tail and not tail.startswith("+"):
            return tail.lstrip("@")
    return raw.lstrip("@")


def format_channel_ref_for_view(channel_ref: str) -> str:
    value = channel_ref.strip()
    if value.startswith("@"):
        return value
    if value.lstrip("-").isdigit():
        return value
    return f"@{value}"


def task_channel_key(channel_username: str) -> str:
    value = (channel_username or "").strip()
    if value.lstrip("-").isdigit():
        return value
    return value.lstrip("@").lower()


async def ensure_default_settings(db: AsyncSession):
    for key, value in DEFAULT_SETTINGS.items():
        exists = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = exists.scalar_one_or_none()
        if not setting:
            db.add(SystemSetting(key=key, value=value))
        elif key == "subscriber_price" and setting.value in {"0.05", "0.10"}:
            setting.value = "0.30"
        elif key == "task_reward" and setting.value in {"0.05", "0.10"}:
            setting.value = "0.30"
        elif key == "daily_bonus_max" and setting.value == "0.10":
            setting.value = "1.00"
        elif key == "deposit_rate" and setting.value == "13000":
            setting.value = "25000"
    await db.commit()


async def get_setting(db: AsyncSession, key: str, default: str | None = None) -> str | None:
    result = await db.execute(select(SystemSetting.value).where(SystemSetting.key == key))
    value = result.scalar_one_or_none()
    if value is None and default is not None:
        await set_setting(db, key, default)
        return default
    return value


async def get_setting_float(db: AsyncSession, key: str, default: float) -> float:
    value = await get_setting(db, key, str(default))
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


async def set_setting(db: AsyncSession, key: str, value: str):
    current = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = current.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.commit()


async def get_all_settings(db: AsyncSession):
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key.asc()))
    return result.scalars().all()


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, telegram_id: int, username: str, first_name: str, referrer_id: int | None = None):
    referral_id = str(uuid.uuid4())[:8]
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referral_id=referral_id,
        referrer_id=referrer_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_balance(db: AsyncSession, user_id: int, amount: float):
    user = await get_user_by_id(db, user_id)
    if not user:
        return 0.0
    new_balance = max(0.0, float(user.balance or 0.0) + float(amount))
    user.balance = round(new_balance, 4)
    await db.commit()
    return user.balance


async def get_user_balance(db: AsyncSession, user_id: int):
    result = await db.execute(select(User.balance).where(User.id == user_id))
    balance = float(result.scalar() or 0.0)
    if balance < 0:
        await db.execute(update(User).where(User.id == user_id).values(balance=0.0))
        await db.commit()
        return 0.0
    return balance


async def get_active_tasks(db: AsyncSession):
    result = await db.execute(select(Task).where(Task.active.is_(True)).order_by(Task.id.asc()))
    return result.scalars().all()


async def create_task(db: AsyncSession, channel_username: str, reward: float, order_id: int | None = None):
    task = Task(channel_username=channel_username, reward=reward, order_id=order_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task_by_id(db: AsyncSession, task_id: int):
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def claim_task_for_completion(db: AsyncSession, task_id: int) -> bool:
    result = await db.execute(
        update(Task)
        .where(and_(Task.id == task_id, Task.active.is_(True)))
        .values(active=False)
    )
    await db.commit()
    return bool(result.rowcount)


async def reactivate_task(db: AsyncSession, task_id: int):
    await db.execute(update(Task).where(Task.id == task_id).values(active=True))
    await db.commit()


async def check_task_completed(db: AsyncSession, user_id: int, task_id: int):
    result = await db.execute(
        select(CompletedTask).where(and_(CompletedTask.user_id == user_id, CompletedTask.task_id == task_id))
    )
    return result.scalar_one_or_none() is not None


async def get_user_completed_channel_keys(db: AsyncSession, user_id: int) -> set[str]:
    result = await db.execute(
        select(Task.channel_username)
        .join(CompletedTask, CompletedTask.task_id == Task.id)
        .where(CompletedTask.user_id == user_id)
    )
    return {task_channel_key(channel) for channel in result.scalars().all() if channel}


async def has_user_completed_channel(db: AsyncSession, user_id: int, channel_username: str) -> bool:
    completed = await get_user_completed_channel_keys(db, user_id)
    return task_channel_key(channel_username) in completed


async def get_user_task_completion_count_since(db: AsyncSession, user_id: int, since: datetime) -> int:
    result = await db.execute(
        select(func.count(CompletedTask.id)).where(
            and_(CompletedTask.user_id == user_id, CompletedTask.completed_at >= since)
        )
    )
    return int(result.scalar() or 0)


async def create_task_skip_event(db: AsyncSession, user_id: int):
    db.add(TaskSkipEvent(user_id=user_id))
    await db.commit()


async def get_user_task_skip_count_since(db: AsyncSession, user_id: int, since: datetime) -> int:
    result = await db.execute(
        select(func.count(TaskSkipEvent.id)).where(
            and_(TaskSkipEvent.user_id == user_id, TaskSkipEvent.created_at >= since)
        )
    )
    return int(result.scalar() or 0)


async def get_oldest_user_task_skip_since(db: AsyncSession, user_id: int, since: datetime):
    result = await db.execute(
        select(TaskSkipEvent.created_at)
        .where(and_(TaskSkipEvent.user_id == user_id, TaskSkipEvent.created_at >= since))
        .order_by(TaskSkipEvent.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def mark_task_completed(
    db: AsyncSession,
    user_id: int,
    task_id: int,
    order_owner_user_id: int | None = None,
):
    completed_task = CompletedTask(user_id=user_id, task_id=task_id, order_owner_user_id=order_owner_user_id)
    db.add(completed_task)
    try:
        await db.commit()
        return True
    except IntegrityError:
        await db.rollback()
        return False


async def get_recent_completed_tasks_for_user(db: AsyncSession, user_id: int, within_days: int = 15):
    cutoff = datetime.utcnow() - timedelta(days=within_days)
    result = await db.execute(
        select(CompletedTask, Task)
        .join(Task, Task.id == CompletedTask.task_id)
        .where(
            and_(
                CompletedTask.user_id == user_id,
                CompletedTask.unsubscribed_penalty_applied.is_(False),
                CompletedTask.completed_at >= cutoff,
            )
        )
    )
    return result.all()


async def mark_unsubscribe_penalty_applied(db: AsyncSession, completed_task_id: int):
    await db.execute(
        update(CompletedTask)
        .where(CompletedTask.id == completed_task_id)
        .values(unsubscribed_penalty_applied=True)
    )
    await db.commit()


async def create_order(db: AsyncSession, user_id: int, channel_username: str, subscribers_needed: int, price: float):
    order = Order(
        user_id=user_id,
        channel_username=channel_username,
        subscribers_needed=subscribers_needed,
        price=price,
        status="active",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order_by_id(db: AsyncSession, order_id: int):
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def get_orders_by_user(db: AsyncSession, user_id: int, limit: int = 20):
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_active_orders_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Order)
        .where(and_(Order.user_id == user_id, Order.status == "active"))
        .order_by(Order.created_at.asc())
    )
    return result.scalars().all()


async def get_order_progress(db: AsyncSession, order_id: int):
    order = await get_order_by_id(db, order_id)
    if not order:
        return None

    result = await db.execute(
        select(func.count(func.distinct(CompletedTask.task_id)))
        .select_from(CompletedTask)
        .join(Task, Task.id == CompletedTask.task_id)
        .where(
            and_(
                Task.order_id == order_id,
                CompletedTask.unsubscribed_penalty_applied.is_(False),
            )
        )
    )
    completed = int(result.scalar() or 0)
    needed = int(order.subscribers_needed or 0)
    remaining = max(needed - completed, 0)
    return {
        "order_id": order.id,
        "owner_user_id": order.user_id,
        "needed": needed,
        "completed": completed,
        "remaining": remaining,
        "status": order.status,
    }


async def get_order_last_completion_at(db: AsyncSession, order_id: int):
    result = await db.execute(
        select(func.max(CompletedTask.completed_at))
        .select_from(CompletedTask)
        .join(Task, Task.id == CompletedTask.task_id)
        .where(Task.order_id == order_id)
    )
    return result.scalar_one_or_none()


async def deactivate_active_tasks_for_order(db: AsyncSession, order_id: int):
    await db.execute(
        update(Task)
        .where(and_(Task.order_id == order_id, Task.active.is_(True)))
        .values(active=False)
    )
    await db.commit()


async def set_order_status(db: AsyncSession, order_id: int, status: str):
    await db.execute(update(Order).where(Order.id == order_id).values(status=status))
    await db.commit()


async def get_pending_orders(db: AsyncSession):
    result = await db.execute(select(Order).where(Order.status == "pending"))
    return result.scalars().all()


async def create_transaction(db: AsyncSession, user_id: int, type_: str, amount: float, description: str):
    transaction = Transaction(user_id=user_id, type=type_, amount=amount, description=description)
    db.add(transaction)
    await db.commit()


async def create_referral(db: AsyncSession, referrer_id: int, referred_id: int):
    referral = Referral(referrer_id=referrer_id, referred_id=referred_id)
    db.add(referral)
    await db.commit()


async def update_referral_commission(db: AsyncSession, referrer_id: int, commission: float):
    await db.execute(
        update(Referral)
        .where(Referral.referrer_id == referrer_id)
        .values(commission_earned=Referral.commission_earned + commission)
    )
    await db.commit()


async def has_referral_record(db: AsyncSession, referrer_id: int, referred_id: int) -> bool:
    result = await db.execute(
        select(Referral).where(and_(Referral.referrer_id == referrer_id, Referral.referred_id == referred_id))
    )
    return result.scalar_one_or_none() is not None


async def create_withdraw_request(db: AsyncSession, user_id: int, amount: float, wallet: str):
    withdraw = WithdrawRequest(user_id=user_id, amount=amount, wallet=wallet)
    db.add(withdraw)
    await db.commit()
    await db.refresh(withdraw)
    return withdraw


async def get_pending_withdraws(db: AsyncSession):
    result = await db.execute(select(WithdrawRequest).where(WithdrawRequest.status == "pending"))
    return result.scalars().all()


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User).order_by(User.id.asc()))
    return result.scalars().all()


async def create_topup_request(
    db: AsyncSession,
    user_id: int,
    amount_local: float,
    payment_method: str = "cash",
    payment_note: str | None = None,
):
    topup = TopupRequest(
        user_id=user_id,
        payment_method=payment_method,
        amount_local=amount_local,
        payment_note=payment_note,
        status="pending",
    )
    db.add(topup)
    await db.commit()
    await db.refresh(topup)
    return topup


async def get_pending_topup_requests(db: AsyncSession):
    result = await db.execute(select(TopupRequest).where(TopupRequest.status == "pending").order_by(TopupRequest.created_at.asc()))
    return result.scalars().all()


async def get_topup_request_by_id(db: AsyncSession, request_id: int):
    result = await db.execute(select(TopupRequest).where(TopupRequest.id == request_id))
    return result.scalar_one_or_none()


async def update_topup_request_status(
    db: AsyncSession,
    request_id: int,
    status: str,
    usd_amount: float | None = None,
):
    values = {"status": status}
    if usd_amount is not None:
        values["usd_amount"] = usd_amount
    await db.execute(update(TopupRequest).where(TopupRequest.id == request_id).values(**values))
    await db.commit()


async def can_claim_daily_bonus(db: AsyncSession, user_id: int):
    result = await db.execute(select(User.last_daily_bonus).where(User.id == user_id))
    last_bonus = result.scalar()
    if last_bonus is None:
        return True
    return datetime.utcnow() - last_bonus > timedelta(hours=24)


async def claim_daily_bonus(db: AsyncSession, user_id: int):
    await db.execute(update(User).where(User.id == user_id).values(last_daily_bonus=datetime.utcnow()))
    await db.commit()


async def update_user_banned(db: AsyncSession, user_id: int, banned: bool):
    await db.execute(update(User).where(User.id == user_id).values(banned=banned))
    await db.commit()


async def get_user_stats(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(func.sum(Transaction.amount)).where(and_(Transaction.user_id == user_id, Transaction.amount > 0))
    )
    total_earned = result.scalar() or 0

    result = await db.execute(
        select(func.sum(Transaction.amount)).where(and_(Transaction.user_id == user_id, Transaction.amount < 0))
    )
    total_spent = abs(result.scalar() or 0)

    result = await db.execute(select(func.count(CompletedTask.id)).where(CompletedTask.user_id == user_id))
    completed_tasks = result.scalar() or 0

    result = await db.execute(select(func.count(Referral.id)).where(Referral.referrer_id == user_id))
    referrals = result.scalar() or 0

    return {
        "total_earned": total_earned,
        "total_spent": total_spent,
        "completed_tasks": completed_tasks,
        "referrals": referrals,
    }


async def get_total_stats(db: AsyncSession):
    users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    tasks = (await db.execute(select(func.count(Task.id)))).scalar() or 0
    pending_withdraws = (await db.execute(select(func.count(WithdrawRequest.id)).where(WithdrawRequest.status == "pending"))).scalar() or 0
    return {
        "users": users,
        "orders": orders,
        "tasks": tasks,
        "pending_withdraws": pending_withdraws,
    }


async def add_mandatory_channel(db: AsyncSession, channel_username: str, join_link: str | None = None):
    normalized = normalize_channel_ref(channel_username)
    normalized_join_link = join_link.strip() if join_link else None
    exists = await db.execute(
        select(MandatoryChannel).where(MandatoryChannel.channel_username == normalized)
    )
    current = exists.scalar_one_or_none()
    if current:
        current.active = True
        if normalized_join_link:
            current.join_link = normalized_join_link
    else:
        db.add(MandatoryChannel(channel_username=normalized, join_link=normalized_join_link, active=True))
    await db.commit()


async def deactivate_mandatory_channel(db: AsyncSession, channel_username: str):
    normalized = normalize_channel_ref(channel_username)
    await db.execute(
        update(MandatoryChannel)
        .where(MandatoryChannel.channel_username == normalized)
        .values(active=False)
    )
    await db.commit()


async def get_active_mandatory_channels(db: AsyncSession):
    result = await db.execute(
        select(MandatoryChannel)
        .where(MandatoryChannel.active.is_(True))
        .order_by(MandatoryChannel.created_at.desc())
    )
    return result.scalars().all()


async def get_channels_overview(db: AsyncSession):
    tasks_result = await db.execute(select(Task.channel_username).where(Task.active.is_(True)))
    task_channels = sorted({f"@{c.lstrip('@')}" for c in tasks_result.scalars().all() if c})

    mandatory_result = await db.execute(
        select(MandatoryChannel).where(MandatoryChannel.active.is_(True))
    )
    mandatory_channels = []
    for channel in mandatory_result.scalars().all():
        mandatory_channels.append(
            {
                "channel": format_channel_ref_for_view(channel.channel_username),
                "join_link": channel.join_link or "-",
            }
        )
    mandatory_channels.sort(key=lambda x: x["channel"])

    return {"task_channels": task_channels, "mandatory_channels": mandatory_channels}
