#!/usr/bin/env python3
"""
Простой скрипт для запуска Telegram-бота 
(работает только при запуске из директории ml_service/bot)
"""
import logging
from main import main

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Запуск бота
    main() 