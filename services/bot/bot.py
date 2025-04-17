"""
Главный файл Telegram бота.
"""
import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Command

from services.bot.services import wait_for_db, wait_for_rabbitmq
from services.bot.handlers import (
    send_welcome,
    handle_text,
    PredictionStates,
    cmd_predict,
    cancel_prediction,
    process_prediction_text,
    cmd_prediction_status, 
    cmd_prediction_history,
    cmd_balance
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
if not API_TOKEN:
    logger.error("Не указан токен API Telegram")
    exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация обработчиков команд
dp.register_message_handler(send_welcome, commands=['start', 'help'])
dp.register_message_handler(cmd_predict, commands=['predict'])
dp.register_message_handler(cancel_prediction, commands=['cancel'], state='*')
dp.register_message_handler(cmd_balance, commands=['balance'])
dp.register_message_handler(cmd_prediction_status, commands=['status'])
dp.register_message_handler(cmd_prediction_history, commands=['history'])

# Регистрация обработчиков состояний
dp.register_message_handler(
    process_prediction_text, 
    state=PredictionStates.waiting_for_text
)

# Обработчик для текстовых сообщений, когда нет активных состояний
dp.register_message_handler(handle_text, content_types=types.ContentTypes.TEXT)

async def on_startup(dp):
    """
    Выполняется при запуске бота.
    """
    logger.info("Запуск бота...")
    
    # Ожидаем доступности базы данных
    if not wait_for_db():
        logger.error("Не удалось подключиться к базе данных")
        exit(1)
    
    # Ожидаем доступности RabbitMQ
    if not wait_for_rabbitmq():
        logger.error("Не удалось подключиться к RabbitMQ")
        exit(1)
    
    logger.info("Бот успешно запущен")

def main():
    """
    Основная функция для запуска бота.
    """
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

if __name__ == '__main__':
    main()