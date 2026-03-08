from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import get_user_by_telegram_id


async def is_user_banned(db: AsyncSession, telegram_id: int) -> bool:
    user = await get_user_by_telegram_id(db, telegram_id)
    return user.banned if user else False


async def validate_user_access(db: AsyncSession, telegram_id: int) -> User:
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise ValueError("Foydalanuvchi topilmadi. /start bosing.")
    if user.banned:
        raise ValueError("Siz bloklangansiz.")
    return user
