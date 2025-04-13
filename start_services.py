#!/usr/bin/env python3
"""
Скрипт для запуска всех сервисов ML Service
"""
import subprocess
import threading
import sys
import os
import time
import logging
import argparse
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

def run_api():
    """Запуск FastAPI сервера"""
    try:
        logger.info("Запуск FastAPI сервера...")
        api_process = subprocess.Popen(
            ["uvicorn", "ml_service.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Читаем и выводим логи API
        for line in api_process.stdout:
            logger.info(f"API: {line.strip()}")
            
        # Если процесс завершился, выводим ошибки
        for line in api_process.stderr:
            logger.error(f"API ERROR: {line.strip()}")
            
        return api_process
    except Exception as e:
        logger.error(f"Ошибка при запуске API: {e}")
        return None

def run_telegram_bot():
    """Запуск Telegram-бота"""
    try:
        logger.info("Ожидаем 5 секунд, чтобы API успел запуститься...")
        time.sleep(5)  # Даем API время на запуск
        
        logger.info("Запуск Telegram-бота...")
        
        # Переходим в директорию с ботом для корректного импорта модулей
        bot_dir = os.path.join(os.getcwd(), "ml_service", "bot")
        
        # Запускаем бота, явно переходя в его директорию
        bot_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=bot_dir,  # Важно: запускаем из директории бота
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Читаем и выводим логи бота
        for line in bot_process.stdout:
            logger.info(f"Bot: {line.strip()}")
            
        # Если процесс завершился, выводим ошибки
        for line in bot_process.stderr:
            logger.error(f"Bot ERROR: {line.strip()}")
            
        return bot_process
    except Exception as e:
        logger.error(f"Ошибка при запуске Telegram-бота: {e}")
        return None

def run_ml_workers(num_workers=3):
    """Запуск ML воркеров"""
    try:
        logger.info(f"Запуск {num_workers} ML воркеров...")
        
        # Путь к скрипту запуска воркеров
        workers_script = os.path.join(os.getcwd(), "ml_service", "rabbitmq", "run_workers.py")
        
        # Запускаем менеджер воркеров
        workers_process = subprocess.Popen(
            [sys.executable, workers_script, "--workers", str(num_workers)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Читаем и выводим логи воркеров
        for line in workers_process.stdout:
            logger.info(f"Workers: {line.strip()}")
            
        # Если процесс завершился, выводим ошибки
        for line in workers_process.stderr:
            logger.error(f"Workers ERROR: {line.strip()}")
            
        return workers_process
    except Exception as e:
        logger.error(f"Ошибка при запуске ML воркеров: {e}")
        return None

def main():
    """Основная функция запуска всех сервисов"""
    parser = argparse.ArgumentParser(description='Запуск ML Service')
    parser.add_argument('--workers', type=int, default=3, help='Количество ML воркеров (по умолчанию 3)')
    parser.add_argument('--no-bot', action='store_true', help='Не запускать Telegram-бота')
    parser.add_argument('--no-workers', action='store_true', help='Не запускать ML воркеров')
    args = parser.parse_args()
    
    try:
        # Запускаем API в отдельном потоке
        api_thread = threading.Thread(target=run_api)
        api_thread.daemon = True
        api_thread.start()
        
        # Даем API время на запуск
        time.sleep(3)
        
        processes = []
        
        # Запускаем воркеров, если требуется
        if not args.no_workers:
            workers_process = run_ml_workers(args.workers)
            if workers_process:
                processes.append(workers_process)
        
        # Запускаем бота, если требуется
        if not args.no_bot:
            bot_process = run_telegram_bot()
            if bot_process:
                processes.append(bot_process)
        
        # Ожидаем завершения работы
        api_thread.join()
        for process in processes:
            process.wait()
            
    except KeyboardInterrupt:
        logger.info("Завершение работы по команде пользователя...")
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
    finally:
        logger.info("Завершение работы всех сервисов")
        sys.exit(0)

if __name__ == "__main__":
    main() 