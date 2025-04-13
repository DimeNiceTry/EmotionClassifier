#!/usr/bin/env python3
"""
Скрипт для запуска нескольких ML воркеров
"""
import sys
import os
import subprocess
import time
import argparse
import threading
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_worker(worker_id):
    """
    Запускает один ML воркер с указанным ID
    
    Args:
        worker_id: Идентификатор воркера
    """
    try:
        logger.info(f"Запуск ML воркера с ID {worker_id}")
        
        # Путь к модулю воркера (относительно корня проекта)
        worker_module = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py")
        
        # Устанавливаем переменную окружения для ID воркера
        env = os.environ.copy()
        env["WORKER_ID"] = f"worker-{worker_id}"
        
        # Запускаем воркер в отдельном процессе
        worker_process = subprocess.Popen(
            [sys.executable, worker_module],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Создаем потоки для чтения вывода
        stdout_thread = threading.Thread(
            target=read_output, 
            args=(worker_process.stdout, f"Worker-{worker_id}")
        )
        stderr_thread = threading.Thread(
            target=read_output, 
            args=(worker_process.stderr, f"Worker-{worker_id}-ERROR")
        )
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        return worker_process
    except Exception as e:
        logger.error(f"Ошибка при запуске воркера {worker_id}: {e}")
        return None

def read_output(pipe, prefix):
    """
    Читает вывод из указанного потока и логирует его
    
    Args:
        pipe: Поток для чтения
        prefix: Префикс для лога
    """
    try:
        for line in pipe:
            logger.info(f"{prefix}: {line.strip()}")
    except Exception as e:
        logger.error(f"Ошибка при чтении вывода {prefix}: {e}")

def main():
    """
    Основная функция для запуска нескольких воркеров
    """
    parser = argparse.ArgumentParser(description='Запуск ML воркеров')
    parser.add_argument('--workers', type=int, default=3, help='Количество воркеров (по умолчанию 3)')
    args = parser.parse_args()
    
    num_workers = args.workers
    logger.info(f"Запуск {num_workers} ML воркеров")
    
    # Запускаем указанное количество воркеров
    worker_processes = []
    try:
        for i in range(1, num_workers + 1):
            process = start_worker(i)
            if process:
                worker_processes.append(process)
            time.sleep(0.5)  # Небольшая задержка между запусками
        
        logger.info(f"Запущено {len(worker_processes)} воркеров")
        
        # Ожидаем завершения воркеров
        for process in worker_processes:
            process.wait()
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем работу воркеров...")
        for process in worker_processes:
            if process:
                process.terminate()
        logger.info("Все воркеры остановлены")
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        for process in worker_processes:
            if process:
                process.terminate()
    finally:
        logger.info("Завершение работы")

if __name__ == "__main__":
    main() 