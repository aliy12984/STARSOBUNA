from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import get_order_progress, get_user_by_id, set_order_status


async def notify_order_progress_update(
    bot: Bot,
    db: AsyncSession,
    order_id: int | None,
    order_owner_id: int | None,
    delta: int,
):
    if not order_id or not order_owner_id or delta == 0:
        return

    progress = await get_order_progress(db, order_id)
    if not progress:
        return

    if progress["remaining"] <= 0 and progress["status"] != "completed":
        await set_order_status(db, order_id, "completed")
        progress["status"] = "completed"
    elif progress["remaining"] > 0 and progress["status"] == "completed":
        await set_order_status(db, order_id, "active")
        progress["status"] = "active"

    owner = await get_user_by_id(db, order_owner_id)
    if not owner:
        return

    if delta > 0:
        delta_line = f"Qo'shildi: <b>+{delta}</b>"
    else:
        delta_line = f"Kamaydi: <b>{delta}</b>"

    text = (
        "Buyurtma progress yangilandi\n"
        f"Buyurtma ID: <b>{progress['order_id']}</b>\n"
        f"{delta_line}\n"
        f"Jami: <b>{progress['completed']}/{progress['needed']}</b>\n"
        f"Qoldi: <b>{progress['remaining']}</b>"
    )
    if progress["remaining"] <= 0:
        text += "\nBuyurtma to'liq bajarildi."

    try:
        await bot.send_message(owner.telegram_id, text)
    except Exception:
        pass
