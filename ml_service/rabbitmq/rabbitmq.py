"""
Модуль для работы с RabbitMQ
"""
import json
import pika
import logging
from typing import Dict, Any, Callable
import os
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Настройки подключения к RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

# Очередь для ML задач
ML_TASK_QUEUE = "ml_tasks"

def get_connection():
    """
    Создает и возвращает соединение с RabbitMQ
    """
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)

def publish_message(message: Dict[str, Any], routing_key: str = ML_TASK_QUEUE):
    """
    Публикует сообщение в очередь RabbitMQ
    
    Args:
        message: Словарь с данными для отправки
        routing_key: Ключ маршрутизации (имя очереди)
    """
    try:
        connection = get_connection()
        channel = connection.channel()
        
        # Объявляем очередь (создастся, если не существует)
        channel.queue_declare(queue=routing_key, durable=True)
        
        # Конвертируем сообщение в JSON
        message_body = json.dumps(message).encode('utf-8')
        
        # Публикуем сообщение
        channel.basic_publish(
            exchange='',
            routing_key=routing_key,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # делает сообщение постоянным
                content_type='application/json'
            )
        )
        
        logger.info(f"Сообщение отправлено в очередь {routing_key}")
        connection.close()
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        raise

def consume_messages(callback: Callable, queue_name: str = ML_TASK_QUEUE):
    """
    Настраивает потребителя сообщений из очереди
    
    Args:
        callback: Функция обратного вызова для обработки сообщений
        queue_name: Имя очереди
    """
    try:
        connection = get_connection()
        channel = connection.channel()
        
        # Объявляем очередь
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Устанавливаем справедливое распределение сообщений
        channel.basic_qos(prefetch_count=1)
        
        # Настраиваем консьюмера
        channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback
        )
        
        logger.info(f"Ожидание сообщений из очереди {queue_name}. Для выхода нажмите CTRL+C")
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Потребитель сообщений остановлен")
        if connection and connection.is_open:
            connection.close()
    except Exception as e:
        logger.error(f"Ошибка в потребителе сообщений: {e}")
        if connection and connection.is_open:
            connection.close()
        raise 