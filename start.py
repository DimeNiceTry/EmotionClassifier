#!/usr/bin/env python3
"""
Скрипт для запуска и управления микросервисами ML системы
"""
import subprocess
import argparse
import sys
import os
import time
import signal
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_services(worker_count=3):
    """
    Запускает все микросервисы с помощью docker-compose
    """
    try:
        logger.info(f"Запуск микросервисов ML системы с {worker_count} воркерами...")
        
        # Запуск всех сервисов
        cmd = ["docker-compose", "up", "-d", "--build", "--scale", f"ml-worker={worker_count}"]
        subprocess.run(cmd, check=True)
        
        logger.info("Микросервисы успешно запущены")
        
        # Выводим информацию о запущенных сервисах
        logger.info("Информация о запущенных сервисах:")
        subprocess.run(["docker-compose", "ps"], check=True)
        
        # Информация о доступе
        logger.info("\nДоступ к сервисам:")
        logger.info("- API: http://localhost:80")
        logger.info("- Swagger: http://localhost:80/docs")
        logger.info("- RabbitMQ: http://localhost:15672 (guest/guest)")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при запуске микросервисов: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return False

def stop_services():
    """
    Останавливает все микросервисы с помощью docker-compose
    """
    try:
        logger.info("Остановка микросервисов ML системы...")
        
        # Остановка всех сервисов
        subprocess.run(["docker-compose", "down"], check=True)
        
        logger.info("Микросервисы успешно остановлены")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при остановке микросервисов: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return False

def check_status():
    """
    Проверяет статус всех микросервисов
    """
    try:
        logger.info("Проверка статуса микросервисов ML системы...")
        
        # Выводим информацию о запущенных сервисах
        subprocess.run(["docker-compose", "ps"], check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при проверке статуса микросервисов: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return False

def view_logs(service=None):
    """
    Просматривает логи микросервисов
    
    Args:
        service: имя сервиса для просмотра логов (None для всех)
    """
    try:
        if service:
            logger.info(f"Просмотр логов сервиса {service}...")
            cmd = ["docker-compose", "logs", "--tail=100", service]
        else:
            logger.info("Просмотр логов всех сервисов...")
            cmd = ["docker-compose", "logs", "--tail=50"]
        
        subprocess.run(cmd, check=True)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при просмотре логов: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return False

def interactive_mode():
    """
    Запускает интерактивный режим управления микросервисами
    """
    print("\nИнтерактивный режим управления микросервисами ML системы")
    print("=" * 60)
    
    while True:
        print("\nДоступные команды:")
        print("  1. Запустить микросервисы")
        print("  2. Остановить микросервисы")
        print("  3. Проверить статус")
        print("  4. Просмотреть логи")
        print("  5. Выход")
        
        choice = input("\nВыберите действие (1-5): ")
        
        if choice == "1":
            workers = input("Укажите количество ML воркеров (по умолчанию 3): ")
            if not workers:
                workers = 3
            start_services(int(workers))
        elif choice == "2":
            stop_services()
        elif choice == "3":
            check_status()
        elif choice == "4":
            service = input("Укажите имя сервиса (или оставьте пустым для всех): ")
            view_logs(service if service else None)
        elif choice == "5":
            print("Выход из программы...")
            break
        else:
            print("Некорректный выбор. Пожалуйста, выберите от 1 до 5.")

def main():
    """
    Главная функция скрипта
    """
    parser = argparse.ArgumentParser(description='Управление микросервисами ML системы')
    parser.add_argument('--start', action='store_true', help='Запустить микросервисы')
    parser.add_argument('--stop', action='store_true', help='Остановить микросервисы')
    parser.add_argument('--status', action='store_true', help='Проверить статус микросервисов')
    parser.add_argument('--logs', metavar='SERVICE', help='Просмотреть логи сервиса (или всех)')
    parser.add_argument('--workers', type=int, default=3, help='Количество ML воркеров (по умолчанию 3)')
    parser.add_argument('--interactive', action='store_true', help='Запустить интерактивный режим')
    
    args = parser.parse_args()
    
    # Запуск интерактивного режима
    if args.interactive or len(sys.argv) == 1:
        interactive_mode()
        return
    
    # Обработка команд
    if args.start:
        start_services(args.workers)
    elif args.stop:
        stop_services()
    elif args.status:
        check_status()
    elif args.logs is not None:
        view_logs(args.logs if args.logs else None)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
        sys.exit(0) 