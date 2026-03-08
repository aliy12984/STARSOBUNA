import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    REDIS_URL = os.getenv("REDIS_URL")
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "").strip()
    BOT_USERNAME = os.getenv("BOT_USERNAME")

    # Rewards
    TASK_REWARD = float(os.getenv("TASK_REWARD", 0.30))
    REFERRAL_COMMISSION = float(os.getenv("REFERRAL_COMMISSION", 0.1))
    DAILY_BONUS = float(os.getenv("DAILY_BONUS", 1.0))
    SUBSCRIBER_PRICE = float(os.getenv("SUBSCRIBER_PRICE", 0.02))

config = Config()
