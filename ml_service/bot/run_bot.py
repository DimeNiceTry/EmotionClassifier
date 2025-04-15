#!/usr/bin/env python3
"""
Скрипт для запуска телеграм бота сервиса ML
"""
import logging
import os
from dotenv import load_dotenv
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Проверка наличия токена
if not os.getenv("TELEGRAM_BOT_TOKEN"):
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    sys.exit(1)

# Импорт после инициализации логирования
from ml_service.bot.bot import main

if __name__ == "__main__":
    logger.info("Запуск Telegram бота ML Service")
    main() 