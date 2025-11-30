import logging
import os
import time

from modules.handlers import (
    RESETTING_BALANCE,
    SETTING_BALANCE,
    cancel_operation,
    handle_message,
    process_balance_input,
    process_reset_balance,
    show_settings_menu,
    show_statistics,
    show_statistics_menu,
    start,
    start_reset_balance,
    start_set_balance,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    # Используем BOT_TOKEN вместо TELEGRAM_BOT_TOKEN
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("❌ BOT_TOKEN environment variable is not set")
        logger.error(
            "❌ Please set BOT_TOKEN in your .env file or environment variables"
        )
        return

    # Даем время для инициализации БД
    time.sleep(10)

    try:
        # Создаем Application вместо Updater
        application = Application.builder().token(token).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))

        # Обработчик для обычных сообщений
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        logger.info("✅ Bot starting...")
        logger.info("✅ Bot is running and waiting for messages...")
        application.run_polling()

    except Exception as e:
        logger.error(f"❌ Bot error: {e}")


if __name__ == "__main__":
    main()
