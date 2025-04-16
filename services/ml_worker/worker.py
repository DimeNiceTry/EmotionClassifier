import logging
import os
import sys
import json
import time
import random
import pika
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import socket
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
ML_TASK_QUEUE = "ml_tasks"
ML_RESULT_QUEUE = "ml_results"

# Настройки PostgreSQL
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Генерируем уникальный идентификатор воркера
WORKER_ID = os.getenv("WORKER_ID", f"worker-{socket.gethostname()}-{random.randint(1000, 9999)}")
logger.info(f"Запуск ML воркера с ID: {WORKER_ID}")

# Функции для работы с БД
def get_db_connection():
    """Создает соединение с базой данных"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise

# Функции для работы с RabbitMQ
def get_rabbitmq_connection():
    """Создает соединение с RabbitMQ"""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

def wait_for_rabbitmq():
    """Ожидает доступности RabbitMQ"""
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к RabbitMQ (попытка {retry_count + 1}/{max_retries})...")
            connection = get_rabbitmq_connection()
            logger.info("Подключение к RabbitMQ успешно установлено")
            connection.close()
            return True
        except Exception as e:
            logger.warning(f"RabbitMQ недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к RabbitMQ после нескольких попыток")
    return False

def wait_for_db():
    """Ожидает доступности базы данных."""
    retry_count = 0
    max_retries = 10
    connection = None
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к PostgreSQL (попытка {retry_count + 1}/{max_retries})...")
            connection = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                dbname="postgres"
            )
            logger.info("Подключение к PostgreSQL успешно установлено")
            connection.close()
            return True
        except psycopg2.OperationalError as e:
            logger.warning(f"PostgreSQL недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к PostgreSQL после нескольких попыток")
    return False

# Функции для ML предсказаний
def validate_data(data):
    """Валидирует входные данные для ML задачи"""
    try:
        # Проверяем наличие необходимых полей
        if not isinstance(data, dict):
            logger.error("Данные не являются словарем")
            return False
        
        required_fields = ["prediction_id", "user_id", "data"]
        for field in required_fields:
            if field not in data:
                logger.error(f"Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем, что data содержит текст
        if not isinstance(data["data"], dict) or "text" not in data["data"]:
            logger.error("В данных отсутствует текст для анализа")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при валидации данных: {e}")
        return False

def make_prediction(input_data):
    """Выполняет предсказание на основе входных данных"""
    # В реальном приложении здесь был бы код для загрузки модели и выполнения предсказания
    # Для демонстрации используем имитацию
    try:
        input_text = input_data.get("text", "").lower()
        
        # Добавляем задержку для имитации работы модели
        time.sleep(random.uniform(1.0, 3.0))
        
        # Список возможных результатов
        possible_results = [
            {"prediction": "Положительный результат", "confidence": round(random.uniform(0.7, 0.95), 2)},
            {"prediction": "Отрицательный результат", "confidence": round(random.uniform(0.6, 0.85), 2)},
            {"prediction": "Неопределенный результат", "confidence": round(random.uniform(0.4, 0.6), 2)}
        ]
        
        # Выбираем результат на основе текста
        if "хорошо" in input_text or "успех" in input_text or "положительно" in input_text:
            result = possible_results[0]
        elif "плохо" in input_text or "неудача" in input_text or "отрицательно" in input_text:
            result = possible_results[1]
        else:
            # Случайный выбор результата
            weights = [0.3, 0.3, 0.4]
            result = random.choices(possible_results, weights=weights, k=1)[0]
        
        # Добавляем дополнительную информацию
        result["timestamp"] = datetime.now().isoformat()
        result["worker_id"] = WORKER_ID
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {e}")
        return {"error": str(e)}

def update_prediction_result(prediction_id, result):
    """Обновляет результат предсказания в базе данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Обновляем предсказание
        cursor.execute(
            """
            UPDATE predictions 
            SET result = %s, status = %s, completed_at = %s
            WHERE id = %s
            """,
            (json.dumps(result), "completed", datetime.now(), prediction_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Результат предсказания {prediction_id} сохранен в БД")
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении результата предсказания: {e}")
        return False

def publish_result(prediction_id, result):
    """Публикует результат предсказания в очередь результатов"""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Объявляем очередь для результатов
        channel.queue_declare(queue=ML_RESULT_QUEUE, durable=True)
        
        # Готовим сообщение
        message = {
            "prediction_id": prediction_id,
            "result": result,
            "worker_id": WORKER_ID,
            "timestamp": datetime.now().isoformat()
        }
        
        # Публикуем сообщение
        channel.basic_publish(
            exchange='',
            routing_key=ML_RESULT_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Сообщение сохраняется при перезагрузке
            )
        )
        
        logger.info(f"Результат предсказания {prediction_id} опубликован в очередь {ML_RESULT_QUEUE}")
        connection.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при публикации результата: {e}")
        return False

def process_message(ch, method, properties, body):
    """Обрабатывает сообщение из очереди"""
    try:
        # Получаем данные
        message = json.loads(body.decode('utf-8'))
        logger.info(f"Воркер {WORKER_ID} получил сообщение: {message.get('prediction_id', 'unknown')}")
        
        # Валидируем данные
        if not validate_data(message):
            logger.error(f"Воркер {WORKER_ID}: сообщение не прошло валидацию")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        prediction_id = message["prediction_id"]
        user_id = message["user_id"]
        data = message["data"]
        
        logger.info(f"Воркер {WORKER_ID}: начинаем обработку предсказания {prediction_id} для пользователя {user_id}")
        
        # Выполняем предсказание
        result = make_prediction(data)
        
        # Обновляем результат в БД
        update_prediction_result(prediction_id, result)
        
        # Публикуем результат в очередь результатов
        publish_result(prediction_id, result)
        
        # Подтверждаем обработку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
        logger.info(f"Воркер {WORKER_ID}: предсказание {prediction_id} обработано успешно")
    except Exception as e:
        logger.error(f"Воркер {WORKER_ID}: ошибка при обработке сообщения: {e}")
        # Подтверждаем сообщение, чтобы не блокировать очередь
        # В реальном приложении можно реализовать механизм повторных попыток
        ch.basic_ack(delivery_tag=method.delivery_tag)

def run_worker():
    """Запускает ML воркер"""
    if not wait_for_rabbitmq():
        logger.error("Невозможно подключиться к RabbitMQ. Выход.")
        return False
    
    if not wait_for_db():
        logger.error("Невозможно подключиться к PostgreSQL. Выход.")
        return False
    
    try:
        logger.info(f"Запуск ML воркера {WORKER_ID}...")
        
        # Создаем соединение с RabbitMQ
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Объявляем очереди для задач и результатов
        channel.queue_declare(queue=ML_TASK_QUEUE, durable=True)
        channel.queue_declare(queue=ML_RESULT_QUEUE, durable=True)
        
        # Устанавливаем справедливую отправку сообщений воркерам
        channel.basic_qos(prefetch_count=1)
        
        # Устанавливаем обработчик сообщений
        channel.basic_consume(
            queue=ML_TASK_QUEUE,
            on_message_callback=process_message
        )
        
        logger.info(f"ML воркер {WORKER_ID} запущен и ожидает сообщения...")
        
        # Начинаем прослушивание очереди
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем работу...")
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске ML воркера: {e}")
        return False

if __name__ == "__main__":
    run_worker() 