from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from keyboards.menu import BTN_MAIN_MENU

BTN_ADMIN_STATS = "📊 Admin statistika"
BTN_ADMIN_BROADCAST = "📢 Xabar yuborish"
BTN_ADMIN_WITHDRAWS = "📤 Pul yechish so'rovlari"
BTN_ADMIN_WITHDRAWS_OLD = "📤 Yechish so'rovlari"
BTN_ADMIN_TOPUP_REQUESTS = "📥 To'ldirish so'rovlari"
BTN_ADMIN_BAN = "🔒 Ban qilish"
BTN_ADMIN_ADD_BALANCE = "➕ Pul qo'shish"
BTN_ADMIN_ADD_BALANCE_LONG = "➕ Foydalanuvchiga pul qo'shish"
BTN_ADMIN_ADD_BALANCE_OLD = "➕ Balans qo'shish"
BTN_ADMIN_SUB_BALANCE = "➖ Pul ayirish"
BTN_ADMIN_SUB_BALANCE_OLD = "➖ Balans ayirish"
BTN_ADMIN_CHANNELS = "📡 Kanal ro'yxati"
BTN_ADMIN_ADD_TASK_CHANNEL = "🎯 Task kanal qo'shish"
BTN_ADMIN_ADD_MANDATORY = "📌 Majburiy kanal qo'shish"
BTN_ADMIN_REMOVE_MANDATORY = "🗑 Majburiy kanal o'chirish"
BTN_ADMIN_SET_REF = "🤝 Referral pulini sozlash"
BTN_ADMIN_SET_TASK_REWARD = "💠 Task narxini sozlash"
BTN_ADMIN_SET_SKIP_LIMIT = "⏱ Skip limit sozlash"
BTN_ADMIN_SET_SKIP_WINDOW = "🕒 Skip oynasi (daq)"
BTN_ADMIN_SET_RATE = "💱 Kursni sozlash"
BTN_ADMIN_SET_CONTACT = "👤 Admin aloqasini sozlash"


def get_admin_menu():
    keyboard = [
        [KeyboardButton(text=BTN_ADMIN_STATS), KeyboardButton(text=BTN_ADMIN_CHANNELS)],
        [KeyboardButton(text=BTN_ADMIN_ADD_TASK_CHANNEL), KeyboardButton(text=BTN_ADMIN_ADD_MANDATORY)],
        [KeyboardButton(text=BTN_ADMIN_REMOVE_MANDATORY), KeyboardButton(text=BTN_ADMIN_SET_REF)],
        [KeyboardButton(text=BTN_ADMIN_SET_TASK_REWARD), KeyboardButton(text=BTN_ADMIN_SET_RATE)],
        [KeyboardButton(text=BTN_ADMIN_SET_SKIP_LIMIT), KeyboardButton(text=BTN_ADMIN_SET_SKIP_WINDOW)],
        [KeyboardButton(text=BTN_ADMIN_SET_CONTACT)],
        [KeyboardButton(text=BTN_ADMIN_TOPUP_REQUESTS)],
        [KeyboardButton(text=BTN_ADMIN_WITHDRAWS)],
        [KeyboardButton(text=BTN_ADMIN_BROADCAST)],
        [KeyboardButton(text=BTN_ADMIN_BAN)],
        [KeyboardButton(text=BTN_ADMIN_ADD_BALANCE), KeyboardButton(text=BTN_ADMIN_SUB_BALANCE)],
        [KeyboardButton(text=BTN_MAIN_MENU)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin bo'limini tanlang...",
    )
