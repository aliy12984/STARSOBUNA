from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import config

engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _column_exists(conn, table_name: str, column_name: str) -> bool:
    rows = (await conn.exec_driver_sql(f"PRAGMA table_info({table_name})")).fetchall()
    return any(r[1] == column_name for r in rows)


async def upgrade_schema():
    async with engine.begin() as conn:
        if not await _column_exists(conn, "tasks", "order_id"):
            await conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN order_id INTEGER")

        if not await _column_exists(conn, "completed_tasks", "order_owner_user_id"):
            await conn.exec_driver_sql("ALTER TABLE completed_tasks ADD COLUMN order_owner_user_id INTEGER")
        if not await _column_exists(conn, "completed_tasks", "unsubscribed_penalty_applied"):
            await conn.exec_driver_sql(
                "ALTER TABLE completed_tasks ADD COLUMN unsubscribed_penalty_applied BOOLEAN DEFAULT 0"
            )
        await conn.exec_driver_sql(
            """
            DELETE FROM completed_tasks
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM completed_tasks
                GROUP BY user_id, task_id
            )
            """
        )
        await conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_completed_tasks_user_task ON completed_tasks(user_id, task_id)"
        )

        if await _column_exists(conn, "mandatory_channels", "id"):
            if not await _column_exists(conn, "mandatory_channels", "join_link"):
                await conn.exec_driver_sql("ALTER TABLE mandatory_channels ADD COLUMN join_link VARCHAR")

        await conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                id INTEGER PRIMARY KEY,
                channel_username VARCHAR UNIQUE,
                join_link VARCHAR,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                key VARCHAR PRIMARY KEY,
                value VARCHAR NOT NULL,
                updated_at DATETIME
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS topup_requests (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                payment_method VARCHAR DEFAULT 'cash',
                amount_local FLOAT,
                payment_note TEXT,
                usd_amount FLOAT,
                status VARCHAR DEFAULT 'pending',
                created_at DATETIME
            )
            """
        )
        if await _column_exists(conn, "topup_requests", "id"):
            if not await _column_exists(conn, "topup_requests", "payment_method"):
                await conn.exec_driver_sql(
                    "ALTER TABLE topup_requests ADD COLUMN payment_method VARCHAR DEFAULT 'cash'"
                )
        await conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS task_skip_events (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                created_at DATETIME
            )
            """
        )


async def get_db():
    async with async_session() as session:
        yield session
