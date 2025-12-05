import logging
import re
from datetime import datetime, timedelta

from modules.database import (
    add_transaction,
    create_currency_balance,
    delete_all_user_data,
    delete_user_currency,
    get_transactions,
    get_transactions_by_period,
    get_user_balance,
    get_user_currencies,
    reset_user_balance,
    update_user_currency,
)
from modules.keyboards import (
    get_main_keyboard,
    get_statistics_keyboard,
    get_settings_keyboard,
    get_balance_keyboard,
    get_currencies_keyboard,
    get_delete_currency_keyboard,
    get_cancel_keyboard,
    get_confirmation_keyboard,
)
from modules.message_parser import parse_message
from telegram import Update # type: ignore
from telegram.ext import ContextTypes # type: ignore

logger = logging.getLogger(__name__)

SETTING_BALANCE, RESETTING_BALANCE, DELETING_ALL_DATA, SETTING_CURRENCY = range(4)

CURRENCY_SYMBOLS = {"USD": "$", "CNY": "¥"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        current_balance = get_user_balance(chat_id)

        await update.message.reply_text(
            f'Привет! Отправь операцию в формате: "Категория, Сумма"\n'
            f'Например: "Продукты, 1500" - для расходов\n'
            f'Или: "Зарплата, 50000" - для доходов\n\n'
            f"Доходы: Зарплата, Аванс, Пополнение\n\n"
            f"Текущий баланс: {current_balance:.2f} руб.\n\n"
            f"Используй кнопки для просмотра статистики 📊 или настроек ⚙️",
            reply_markup=get_main_keyboard(),
        )
        logger.info(f"✅ User {chat_id} started the bot")
    except Exception as e:
        logger.error(f"Error in start command: {e}")

# Обработка сообщения
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    # Обработка кнопок
    button_handlers = {
        "📊 Статистика": show_statistics_menu,
        "📅 День": lambda u, c: show_statistics(u, c, "day"),
        "📆 Неделя": lambda u, c: show_statistics(u, c, "week"),
        "📈 Месяц": lambda u, c: show_statistics(u, c, "month"),
        #
        "⚙️ Настройки": show_settings_menu,
        "💰 Ваш баланс": show_balance_menu,
        "💰 Установить баланс": start_set_balance,
        "🔄 Сбросить баланс": start_reset_balance,
        #
        "💱 Валюты": show_currencies_menu,
        "💵 USD": lambda u, c: start_set_currency(u, c, "USD"),
        "💴 CNY": lambda u, c: start_set_currency(u, c, "CNY"),
        "🗑️ Удалить валюту": show_delete_currency_menu,
        "❌ Удалить USD": lambda u, c: delete_currency(u, c, "USD"),
        "❌ Удалить CNY": lambda u, c: delete_currency(u, c, "CNY"),
        #
        "🗑️ Сбросить все данные": start_delete_all_data,
        "⬅️ Назад": show_main_menu,
        "❌ Отмена": cancel_operation,
        "✅ Да": process_delete_all_data,
    }

    if text in button_handlers:
        await button_handlers[text](update, context)
        return

    # Проверяем, находится ли пользователь в процессе установки баланса
    if context.user_data.get("setting_balance"):
        await process_balance_input(update, context)
        return
    elif context.user_data.get("resetting_balance"):
        await process_reset_balance(update, context)
        return
    elif context.user_data.get("deleting_all_data"):
        # Для удаления всех данных используем кнопку подтверждения
        await update.message.reply_text(
            "⚠️ Пожалуйста, используйте кнопки для подтверждения:\n"
            "• '✅ Да, удалить все' - для подтверждения удаления\n"
            "• '❌ Отмена' - для отмены",
            reply_markup=get_confirmation_keyboard(),
        )
        return
    elif context.user_data.get("setting_currency"):
        await process_currency_input(update, context)
        return

    # Обработка обычного сообщения с операцией
    try:
        category, amount, is_income = parse_message(text)
        add_transaction(
            chat_id=chat_id,
            date=datetime.now().date(),
            category=category,
            amount=amount,
            is_income=is_income,
        )

        operation_type = "доход" if is_income else "расход"
        await update.message.reply_text(
            f"✅ Запись добавлена: {category} - {amount} руб. ({operation_type})",
            reply_markup=get_main_keyboard(),
        )
        logger.info(f"✅ User {chat_id} added {operation_type}: {category} - {amount}")
    except ValueError as e:
        await update.message.reply_text(str(e), reply_markup=get_main_keyboard())
        logger.warning(f"User {chat_id} input error: {e}")
    except Exception as e:
        await update.message.reply_text(
            "❌ Произошла ошибка при добавлении записи",
            reply_markup=get_main_keyboard(),
        )
        logger.error(f"Database error for user {chat_id}: {e}")

# Главное меню
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню с балансами"""
    chat_id = update.effective_chat.id
    current_balance = get_user_balance(chat_id)

    # Получаем валютные балансы пользователя
    currencies = get_user_currencies(chat_id)

    # Формируем сообщение с балансами
    message = f"Главное меню\n\n💵 Текущий баланс: {current_balance:.2f} ₽"

    # Добавляем валютные балансы, если они есть
    if currencies:
        message += "\n\n💱 Валютные балансы:\n"
        for currency in currencies:
            symbol = CURRENCY_SYMBOLS.get(currency.currency, currency.currency)
            message += f"• {currency.currency}: {currency.amount:.2f}{symbol}\n"
    else:
        message += "\n\n💱 Валютные балансы отсутствуют\nДля добавления перейдите в Настройки → Валюты"

    await update.message.reply_text(message, reply_markup=get_main_keyboard())

# Меню статистики
async def show_statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню статистики"""
    await update.message.reply_text(
        "Выберите период для просмотра статистики:",
        reply_markup=get_statistics_keyboard(),
    )

# Меню настроек
async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    current_balance = get_user_balance(chat_id)
    transactions = get_transactions(chat_id)
    transactions_count = len(transactions)

    # Получаем количество валют пользователя
    currencies = get_user_currencies(chat_id)
    currencies_count = len(currencies)

    await update.message.reply_text(
        f"⚙️ Настройки\n\n"
        f"Текущий баланс: {current_balance:.2f} руб.\n"
        f"Количество операций: {transactions_count}\n"
        f"Количество валют: {currencies_count}\n\n"
        f"Выберите действие:",
        reply_markup=get_settings_keyboard(),
    )

''' Функции для работы с балансом '''

# Меню баланса
async def show_balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_balance = get_user_balance(chat_id)

    message = "💱 Управление балансом\n\n"

    if current_balance:
        message += f"Текущий баланс: {current_balance:.2f} ₽\n"
        current_balance = get_user_balance(chat_id)
    else:
        message += "У вас нет денег на счету\n"

    message += "Выберите дальнейшее действие:"

    await update.message.reply_text(message, reply_markup=get_balance_keyboard())

# Установка баланса
async def start_set_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_balance = get_user_balance(chat_id)

    context.user_data["setting_balance"] = True

    await update.message.reply_text(
        f"💰 Установка баланса\n\n"
        f"Текущий баланс: {current_balance:.2f} руб.\n\n"
        f"Введите новое значение баланса (например: 10000 или 1500.50):\n"
        f"Или нажмите '❌ Отмена' для возврата",
        reply_markup=get_cancel_keyboard(),
    )

# Ввод баланса в базу данных? Надо проверить в /dev, пока не удаляем в мейн ветке (НО ТАМ ПОСОС ФУНКЦИЯ)
async def process_balance_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    try:
        # Парсим число, убираем пробелы и заменяем запятые на точки
        balance_text = text.replace(" ", "").replace(",", ".")
        new_balance = float(balance_text)

        # Устанавливаем новый баланс
        reset_user_balance(chat_id, new_balance)

        # Очищаем состояние
        context.user_data.pop("setting_balance", None)

        await update.message.reply_text(
            f"✅ Баланс успешно установлен: {new_balance:.2f} руб.",
            reply_markup=get_main_keyboard(),
        )
        logger.info(f"✅ User {chat_id} set balance to: {new_balance}")

    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат числа. Введите число (например: 10000 или 1500.50):",
            reply_markup=get_cancel_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error setting balance for user {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при установке баланса",
            reply_markup=get_main_keyboard(),
        )
        context.user_data.pop("setting_balance", None)

# Начало удаления баланса
async def start_reset_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_balance = get_user_balance(chat_id)

    context.user_data["resetting_balance"] = True

    await update.message.reply_text(
        f"🔄 Сброс баланса\n\n"
        f"Текущий баланс: {current_balance:.2f} руб.\n\n"
        f"Вы уверены, что хотите сбросить баланс до 0?\n"
        f"Это действие нельзя отменить!\n\n"
        f"Введите 'ДА' для подтверждения или '❌ Отмена' для отмены:",
        reply_markup=get_cancel_keyboard(),
    )

# Удаление баланса
async def process_reset_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().upper()

    if text == "ДА":
        try:
            # Сбрасываем баланс
            reset_user_balance(chat_id, 0)

            # Очищаем состояние
            context.user_data.pop("resetting_balance", None)

            await update.message.reply_text(
                "✅ Баланс успешно сброшен до 0 руб.", reply_markup=get_main_keyboard()
            )
            logger.info(f"✅ User {chat_id} reset balance to 0")

        except Exception as e:
            logger.error(f"Error resetting balance for user {chat_id}: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при сбросе баланса",
                reply_markup=get_main_keyboard(),
            )
            context.user_data.pop("resetting_balance", None)
    else:
        await update.message.reply_text(
            "❌ Сброс баланса отменен. Введите 'ДА' для подтверждения или '❌ Отмена' для выхода:",
            reply_markup=get_cancel_keyboard(),
        )


''' Функции для работы с данными '''

# Начало удаления всех данных
async def start_delete_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Получаем статистику пользователя
    transactions = get_transactions(chat_id)
    transactions_count = len(transactions)
    current_balance = get_user_balance(chat_id)

    context.user_data["deleting_all_data"] = True

    await update.message.reply_text(
        f"🗑️ Сброс всех данных\n\n"
        f"⚠️ ⚠️ ⚠️ ВНИМАНИЕ! ⚠️ ⚠️ ⚠️\n\n"
        f"Это действие УДАЛИТ ВСЕ ваши данные:\n"
        f"• Операций расходов/доходов: {transactions_count}\n"
        f"• Текущий баланс: {current_balance:.2f} руб.\n\n"
        f"❌ Это действие НЕЛЬЗЯ отменить!\n"
        f"❌ Данные будут удалены НАВСЕГДА!\n\n"
        f"Для подтверждения нажмите '✅ ДА, удалить все'\n"
        f"Для отмены нажмите '❌ Отмена'",
        reply_markup=get_confirmation_keyboard(),
    )

# Удаление всех данных
async def process_delete_all_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    try:
        # Удаляем все данные пользователя
        transactions_deleted, balance_deleted, currencies_deleted = (
            delete_all_user_data(chat_id)
        )

        # Очищаем состояние
        context.user_data.pop("deleting_all_data", None)

        await update.message.reply_text(
            f"✅ Все данные успешно удалены!\n\n"
            f"Удалено:\n"
            f"• Операций расходов/доходов: {transactions_deleted}\n"
            f"• Записей баланса: {balance_deleted}\n"
            f"• Валютных балансов: {currencies_deleted}\n\n"
            f"Бот готов к работе с чистого листа!",
            reply_markup=get_main_keyboard(),
        )
        logger.info(
            f"✅ User {chat_id} deleted all data: {transactions_deleted} transactions, {balance_deleted} balance records, {currencies_deleted} currency records"
        )

    except Exception as e:
        logger.error(f"Error deleting all data for user {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при удалении данных", reply_markup=get_main_keyboard()
        )
        context.user_data.pop("deleting_all_data", None)

# Отмена операции? Тоже надо проверить
async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Очищаем состояния
    context.user_data.pop("setting_balance", None)
    context.user_data.pop("resetting_balance", None)
    context.user_data.pop("deleting_all_data", None)
    context.user_data.pop("setting_currency", None)

    chat_id = update.effective_chat.id
    current_balance = get_user_balance(chat_id)

    await update.message.reply_text(
        f"Операция отменена.\n\nТекущий баланс: {current_balance:.2f} руб.",
        reply_markup=get_main_keyboard(),
    )
    logger.info(f"✅ User {chat_id} cancelled operation")


''' Функции для работы с валютами '''

async def show_currencies_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    currencies = get_user_currencies(chat_id)

    message = "💱 Управление валютами\n\n"

    if currencies:
        message += "Ваши валютные балансы:\n"
        for currency in currencies:
            symbol = CURRENCY_SYMBOLS.get(currency.currency, currency.currency)
            message += f"• {currency.currency}: {currency.amount:.2f}{symbol}\n"
        message += "\n"
    else:
        message += "У вас пока нет валютных балансов\n\n"

    message += "Нажмите на валюту чтобы открыть её баланс:"

    await update.message.reply_text(message, reply_markup=get_currencies_keyboard())


async def show_delete_currency_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    currencies = get_user_currencies(chat_id)

    if not currencies:
        await update.message.reply_text(
            "❌ У вас нет валютных балансов для удаления",
            reply_markup=get_currencies_keyboard(),
        )
        return

    await update.message.reply_text(
        reply_markup=get_delete_currency_keyboard(currencies),
    )


async def start_set_currency(update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
    chat_id = update.effective_chat.id

    context.user_data["setting_currency"] = currency

    symbol = CURRENCY_SYMBOLS.get(currency, currency)

    await update.message.reply_text(
        f"💵 Установка баланса {currency}\n\n"
        f"Введите сумму в {currency} (например: 100 или 150.50):\n"
        f"Или нажмите '❌ Отмена' для возврата",
        reply_markup=get_cancel_keyboard(),
    )


async def open_currency_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
    chat_id = update.effective_chat.id

    try:
        # Создаем валютный баланс (если не существует)
        current_balance = create_currency_balance(chat_id, currency)

        symbol = CURRENCY_SYMBOLS.get(currency, currency)

        await update.message.reply_text(
            f"✅ Открыт валютный баланс {currency}\n\n"
            f"Текущий баланс: {current_balance:.2f}{symbol}\n\n"
            f"Для пополнения используйте: '{currency}, 50'\n"
            f"Для списания используйте: '{currency}, -30'",
            reply_markup=get_currencies_keyboard(),
        )
        logger.info(f"✅ User {chat_id} opened {currency} balance: {current_balance}")

    except Exception as e:
        logger.error(f"Error opening {currency} balance for user {chat_id}: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при открытии баланса {currency}",
            reply_markup=get_currencies_keyboard(),
        )


async def process_currency_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    currency = context.user_data.get("setting_currency")

    try:
        # Парсим число, убираем пробелы и заменяем запятые на точки
        amount_text = text.replace(" ", "").replace(",", ".")
        amount = float(amount_text)

        # Устанавливаем валютный баланс
        update_user_currency(chat_id, currency, amount)

        # Очищаем состояние
        context.user_data.pop("setting_currency", None)

        symbol = CURRENCY_SYMBOLS.get(currency, currency)

        await update.message.reply_text(
            f"✅ Баланс {currency} успешно установлен: {amount:.2f}{symbol}",
            reply_markup=get_currencies_keyboard(),
        )
        logger.info(f"✅ User {chat_id} set {currency} balance to: {amount}")

    except ValueError:
        symbol = CURRENCY_SYMBOLS.get(currency, currency)
        await update.message.reply_text(
            f"❌ Неверный формат числа. Введите сумму в {currency} (например: 100 или 150.50):",
            reply_markup=get_cancel_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error setting {currency} balance for user {chat_id}: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при установке баланса {currency}",
            reply_markup=get_currencies_keyboard(),
        )
        context.user_data.pop("setting_currency", None)


async def delete_currency(update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
    chat_id = update.effective_chat.id

    try:
        deleted = delete_user_currency(chat_id, currency)

        if deleted:
            await update.message.reply_text(
                f"✅ Баланс {currency} успешно удален",
                reply_markup=get_currencies_keyboard(),
            )
            logger.info(f"✅ User {chat_id} deleted {currency} balance")
        else:
            await update.message.reply_text(
                f"❌ Баланс {currency} не найден",
                reply_markup=get_currencies_keyboard(),
            )

    except Exception as e:
        logger.error(f"Error deleting {currency} balance for user {chat_id}: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при удалении баланса {currency}",
            reply_markup=get_currencies_keyboard(),
        )

''' Функции для статистики '''

# Отрисовка статистики
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE, period_type: str):
    try:
        chat_id = update.effective_chat.id

        start_date, end_date, period_name = get_period_dates(period_type)   # Получаем даты периода

        transactions = get_transactions_by_period(chat_id, start_date, end_date) # Получаем транзакции за период
        stats = calculate_statistics(transactions)  # Вызываем функцию подсчёта статистики

        # Формируем сообщение, заголовок
        message = f"───────── • ✦ • ─────────\n"
        message += f"                    Статистика\n"
        message += f"       {period_name}\n"
        message += f"───────── • ✦ • ─────────\n\n"

        # Доходы
        if stats["income"]:
            message += "📈 Доходы:\n"
            for category, amount in stats['income']:
                message += f"      • {category}: {amount:.2f} ₽\n\n"
            message += f"      • Итого: {stats['total_income']:.2f} ₽\n\n"
        else:                           #{period_name.split(' ')[0]}: 
            message += f"      • Доходов за {period_name.split(' ')[0]} не было\n\n"

        # Расходы
        if stats["expenses"]:
            message += "📉 Расходы:\n"
            for category, amount in stats['expenses']:
                message += f"      • {category}: {amount:.2f} ₽\n\n"
            message += f"      • Итого: {stats['total_expenses']:.2f} ₽\n\n"
        else:
            message += f"      • Расходов за {period_name.split(' ')[0]} не было\n\n"

        # Убыток/доход
        if stats["daily_balance"]:
            net_income = stats["daily_balance"]
            if net_income < 0:
                message += f"🔻 Убыток: {net_income:.2f} ₽\n\n"
            elif net_income > 0:
                message += f"🔺️ Прибыль: {net_income:.2f} ₽\n\n"
            else:
                message += f"Сегодня вы вышли в ноль\n\n"

        # Итог и валюты
        current_balance = get_user_balance(chat_id)

        currencies = get_user_currencies(chat_id)
        currency_text = ""

        for currency in currencies:
            symbol = CURRENCY_SYMBOLS.get(currency.currency, currency.currency)
            currency_text += f"  |  {currency.amount:.2f} {symbol}"
            
        if currency_text:
            message = f"───────── • ✦ • ─────────\n"
            message += f"                        Баланс"
            message += f"  {current_balance:.2f} ₽{currency_text}"
            message = f"───────── • ✦ • ─────────\n"
        else:
            message = f"───────── • ✦ • ─────────\n"
            message += f"                        Баланс"
            message += f"                      {current_balance:.2f} ₽"
            message = f"───────── • ✦ • ─────────\n"

        await update.message.reply_text(message, reply_markup=get_statistics_keyboard())
        logger.info(f"✅ User {chat_id} viewed {period_type} statistics")

    except Exception as e:
        logger.error(f"Error in {period_type} statistics for user {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении статистики", reply_markup=get_statistics_keyboard()
        )

# Рассчёт статистики
def calculate_statistics(transactions):
    expenses_by_category = {}   # Расходы по категориям (я так понимаю)
    income_by_category = {} # Поступления по категориям (я так понимаю)
    total_expenses = 0  # Итоговые расходы
    total_income = 0    # Итоговые доходы
    
    for transaction in transactions:    # Для транзакций из таблицы
        if transaction.type == 'income':    # Если тип транзакции - поступление
            category = transaction.category # Группируем расходы по категориям
            if category not in income_by_category:  # Если категория не в списке
                income_by_category[category] = 0    # Доход по категориям равен нулю
            income_by_category[category] += transaction.amount  # Доход по категории += сумме транзакции
            total_income += transaction.amount  # Итоговый доход += Сумме транзакции
        else:
            category = transaction.category # Группируем расходы по категориям
            if category not in expenses_by_category:    # Если категория не в списке
                expenses_by_category[category] = 0  # Расход по категориям равен нулю
            expenses_by_category[category] += transaction.amount # Расход по категории += сумме транзакции
            total_expenses += transaction.amount    # Итоговый расход += Сумме транзакции
    
    daily_balance = total_income - total_expenses   # Выхлоп за сегодня (чистый доход/расход)   доходы-расходы
    
    return {    # Возвращает
        'expenses_by_category': expenses_by_category,   # Траты по категориям
        'income_by_category': income_by_category,   # Доходы по категориям
        'expenses': list(expenses_by_category.items()),  # Список кортежей (категория, сумма)
        'income': list(income_by_category.items()), # Список кортежей (категория, сумма)
        'total_expenses': total_expenses,   # Итоговые траты
        'total_income': total_income,   # Итоговые доходы
        'daily_balance': daily_balance # Выхлоп за сегодня (чистый доход/расход)
    }

#Получение периода для рассчёта статистики
def get_period_dates(period_type):
    today = datetime.now().date()

    if period_type == "day": 
        start_date = today
        end_date = today
        period_name = f"Сегодня ({start_date} - {end_date})"
    elif period_type == "week":
        start_date = today - timedelta(days=7)
        end_date = today
        period_name = f"Неделю ({start_date} - {end_date})"
    elif period_type == "month":
        start_date = today.replace(day=1)
        end_date = today
        period_name = f"Месяц ({start_date} - {end_date})"

    return start_date, end_date, period_name

# Иконки для периода. Непонятно, надо ли так оставить
def get_period_icon(period_type):
    icons = {"day": "📅", "week": "📆", "month": "📈"}
    return icons.get(period_type, "📊")
