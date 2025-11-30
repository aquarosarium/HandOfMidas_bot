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
        [KeyboardButton("💰 Установить баланс")],
        [KeyboardButton("🔄 Сбросить баланс")],
        [KeyboardButton("💱 Валюты")],
        [KeyboardButton("🗑️ Сбросить все данные")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Меню валют
def get_currencies_keyboard():
    keyboard = [
        [KeyboardButton("💵 USD")],
        [KeyboardButton("💴 CNY")],
        [KeyboardButton("🗑️ Удалить валюту")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_usd_keyboard():
    keyboard = [[KeyboardButton("📊 Купить USD")], [KeyboardButton("⬅️ Назад")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cny_keyboard():
    keyboard = [[KeyboardButton("📊 Купить CNY")], [KeyboardButton("⬅️ Назад")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Меню удаления валюты
def get_delete_currency_keyboard(user_currencies):
    """Создает клавиатуру для удаления валют на основе имеющихся у пользователя"""
    keyboard = []
    for currency in user_currencies:
        if currency.currency == "USD":
            keyboard.append([KeyboardButton("❌ Удалить USD")])
        elif currency.currency == "CNY":
            keyboard.append([KeyboardButton("❌ Удалить CNY")])

    keyboard.append([KeyboardButton("⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Клавиатура для отмены действия
def get_cancel_keyboard():
    keyboard = [[KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Клавиатура для подтверждения опасных действий
def get_confirmation_keyboard():
    keyboard = [[KeyboardButton("✅ ДА, удалить все")], [KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
