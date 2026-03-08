from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_EARN = "💸 Pul ishlash"
BTN_ORDER = "📦 Buyurtma berish"
BTN_MY_ORDERS = "📊 Mening buyurtmalarim"
BTN_REFERRAL = "🤝 Referral dastur"
BTN_BALANCE = "💳 Mening balansim"
BTN_DAILY_BONUS = "🎁 Kunlik bonus"
BTN_TOPUP = "💰 Hisobni to'ldirish"
BTN_WITHDRAW = "🏧 Pul yechish"
BTN_STATS = "📈 Statistikalar"
BTN_HELP = "🛟 Yordam"
BTN_MAIN_MENU = "🏠 Asosiy menyu"

BTN_CHECK_SUB = "✅ Obunani tekshirish"
BTN_NEXT_TASK = "⏭ Keyingi vazifa"

BTN_CONFIRM_ORDER = "✅ Buyurtmani tasdiqlash"
BTN_CANCEL = "❌ Bekor qilish"

BTN_BANK = "💳 Bank karta"
BTN_CRYPTO = "🪙 Kripto wallet"

MAIN_MENU_BUTTONS = [
    BTN_EARN,
    BTN_ORDER,
    BTN_MY_ORDERS,
    BTN_REFERRAL,
    BTN_BALANCE,
    BTN_DAILY_BONUS,
    BTN_TOPUP,
    BTN_WITHDRAW,
    BTN_STATS,
    BTN_HELP,
    BTN_MAIN_MENU,
]


def get_main_menu():
    keyboard = [
        [KeyboardButton(text=BTN_EARN), KeyboardButton(text=BTN_ORDER)],
        [KeyboardButton(text=BTN_MY_ORDERS), KeyboardButton(text=BTN_BALANCE)],
        [KeyboardButton(text=BTN_TOPUP), KeyboardButton(text=BTN_WITHDRAW)],
        [KeyboardButton(text=BTN_REFERRAL), KeyboardButton(text=BTN_DAILY_BONUS)],
        [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_HELP)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Bo'limni tanlang...",
    )


def get_task_menu():
    keyboard = [
        [KeyboardButton(text=BTN_CHECK_SUB), KeyboardButton(text=BTN_NEXT_TASK)],
        [KeyboardButton(text=BTN_MAIN_MENU)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Vazifani tekshiring yoki keyingisiga o'ting...",
    )


def get_order_menu():
    keyboard = [
        [KeyboardButton(text=BTN_CONFIRM_ORDER), KeyboardButton(text=BTN_CANCEL)],
        [KeyboardButton(text=BTN_MAIN_MENU)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Tasdiqlang yoki bekor qiling...",
    )


def get_withdraw_menu():
    keyboard = [
        [KeyboardButton(text=BTN_BANK), KeyboardButton(text=BTN_CRYPTO)],
        [KeyboardButton(text=BTN_MAIN_MENU)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="To'lov usulini tanlang...",
    )
