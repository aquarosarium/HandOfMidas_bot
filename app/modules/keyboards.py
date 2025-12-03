from telegram import KeyboardButton, ReplyKeyboardMarkup

# Главное меню
def get_main_keyboard():
    keyboard = [[KeyboardButton("📊 Статистика")], [KeyboardButton("⚙️ Настройки")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Меню статистики
def get_statistics_keyboard():
    keyboard = [
        [KeyboardButton("📅 День")],
        [KeyboardButton("📆 Неделя")],
        [KeyboardButton("📈 Месяц")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Меню настроек
def get_settings_keyboard():
    keyboard = [
        [KeyboardButton("💰 Ваш баланс")],
        [KeyboardButton("💱 Валюты")],
        [KeyboardButton("🗑️ Сбросить все данные")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Меню настроек
def get_balance_keyboard():
    keyboard = [
        [KeyboardButton("💰 Установить баланс")],
        [KeyboardButton("🔄 Сбросить баланс")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Меню валют
def get_currencies_keyboard():
    keyboard = [
        [KeyboardButton("💵 USD")],
        [KeyboardButton("💴 CNY")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Меню доллара
def get_usd_keyboard():
    keyboard = [
        [KeyboardButton("💵 Добавить USD")],
        [KeyboardButton("🗑️ Удалить USD")],
        [KeyboardButton("⬅️ Меню валют")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Меню юани
def get_cny_keyboard():
    keyboard = [
        [KeyboardButton("💴 Добавить CNY")],
        [KeyboardButton("🗑️ Удалить CNY")],
        [KeyboardButton("⬅️ Меню валют")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура для отмены действия
def get_cancel_keyboard():
    keyboard = [[KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура для подтверждения опасных действий
def get_confirmation_keyboard():
    keyboard = [[KeyboardButton("✅ Да")], [KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
