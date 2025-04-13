#!/usr/bin/env python3
"""
Скрипт для запуска одного ML воркера
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def main():
    """
    Основная функция для запуска одного воркера
    """
    parser = argparse.ArgumentParser(description='Запуск одного ML воркера')
    parser.add_argument('--id', type=int, default=1, help='ID воркера')
    args = parser.parse_args()
    
    # Устанавливаем переменную окружения для ID воркера
    os.environ["WORKER_ID"] = f"worker-{args.id}"
    
    # Импортируем и запускаем воркер
    from ml_service.rabbitmq.worker import run_worker
    run_worker()

if __name__ == "__main__":
    main() 