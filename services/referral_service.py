from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.queries import (
    create_referral,
    get_setting_float,
    get_user_by_telegram_id,
    has_referral_record,
)
from utils.reward_system import add_referral_commission


class ReferralService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_referral_link(self, telegram_id: int) -> str:
        username = (config.BOT_USERNAME or "").lstrip("@")
        return f"https://t.me/{username}?start={telegram_id}"

    async def process_referral_join(self, new_user_id: int, referrer_telegram_id: int):
        referrer = await get_user_by_telegram_id(self.db, referrer_telegram_id)
        if not referrer:
            return
        if await has_referral_record(self.db, referrer.id, new_user_id):
            return

        await create_referral(self.db, referrer.id, new_user_id)
        referral_reward = await get_setting_float(self.db, "referral_reward", 0.10)
        await add_referral_commission(self.db, referrer.id, referral_reward)
