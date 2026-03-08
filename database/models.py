from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    balance = Column(Float, default=0.0)
    referral_id = Column(String, unique=True)
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_daily_bonus = Column(DateTime, nullable=True)

    referrer = relationship("User", remote_side=[id])


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    channel_username = Column(String)
    reward = Column(Float)
    active = Column(Boolean, default=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CompletedTask(Base):
    __tablename__ = "completed_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "task_id", name="uq_completed_tasks_user_task"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    order_owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    unsubscribed_penalty_applied = Column(Boolean, default=False)
    completed_at = Column(DateTime, default=datetime.utcnow)


class TaskSkipEvent(Base):
    __tablename__ = "task_skip_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    channel_username = Column(String)
    subscribers_needed = Column(Integer)
    price = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)
    amount = Column(Float)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("users.id"))
    referred_id = Column(Integer, ForeignKey("users.id"))
    commission_earned = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    wallet = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class TopupRequest(Base):
    __tablename__ = "topup_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    payment_method = Column(String, default="cash")  # cash | stars
    amount_local = Column(Float)
    payment_note = Column(Text, nullable=True)
    usd_amount = Column(Float, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)


class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_username = Column(String, unique=True, index=True)
    join_link = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
