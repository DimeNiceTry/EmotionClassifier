#!/usr/bin/env python3
"""
Скрипт для запуска Telegram-бота ML Service
"""
import logging
import sys
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

try:
    # Импортируем main напрямую из текущего каталога
    from main import main
    
    logger.info("Запуск Telegram-бота ML Service...")
    main()
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    logger.error("Убедитесь, что вы запускаете бота из директории проекта")
    sys.exit(1)
except Exception as e:
    logger.error(f"Ошибка при запуске бота: {e}")
    sys.exit(1) 