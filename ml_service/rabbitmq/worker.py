"""
ML сервис - Воркер для обработки задач машинного обучения
"""
import json
import logging
import sys
import os
import time
from typing import Dict, Any
import random
from datetime import datetime
import pika
import socket

# Добавляем корневой каталог в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml_service.rabbitmq.rabbitmq import consume_messages, ML_TASK_QUEUE
from ml_service.database.database import get_db_session
from ml_service.database.models import Prediction, User, Balance, Transaction

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Генерируем уникальный идентификатор воркера
WORKER_ID = os.getenv("WORKER_ID", f"worker-{socket.gethostname()}-{random.randint(1000, 9999)}")

# Стоимость задачи
PREDICTION_COST = 1.0

def validate_data(data: Dict[str, Any]) -> bool:
    """
    Валидирует входные данные для ML задачи
    
    Args:
        data: Входные данные для проверки
        
    Returns:
        bool: True, если данные прошли валидацию, иначе False
    """
    try:
        # Проверяем ключи, которые должны присутствовать
        required_keys = ["user_id", "input_data"]
        for key in required_keys:
            if key not in data:
                logger.error(f"Отсутствует обязательный ключ: {key}")
                return False
                
        # Проверяем типы данных
        if not isinstance(data["user_id"], int):
            logger.error("Неверный тип для user_id")
            return False
            
        # Проверяем, что input_data содержит текст
        if not isinstance(data["input_data"], dict) or "text" not in data["input_data"]:
            logger.error("Неверный формат для input_data")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Ошибка при валидации данных: {e}")
        return False

def make_ml_prediction(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполняет предсказание на основе входных данных
    
    Args:
        input_data: Входные данные для модели
        
    Returns:
        Dict[str, Any]: Результат предсказания
    """
    # В реальном сценарии здесь была бы загрузка модели и выполнение предикта
    # Для демонстрации используем имитацию предсказания
    
    # Получаем текст запроса или используем пустую строку
    input_text = input_data.get("text", "").lower() if isinstance(input_data, dict) else ""
    
    # Добавляем задержку для имитации работы модели
    time.sleep(random.uniform(0.5, 2.0))
    
    # Список возможных результатов предсказания
    possible_results = [
        {"prediction": "Положительный результат", "confidence": round(random.uniform(0.7, 0.95), 2)},
        {"prediction": "Отрицательный результат", "confidence": round(random.uniform(0.6, 0.85), 2)},
        {"prediction": "Неопределенный результат", "confidence": round(random.uniform(0.4, 0.6), 2)}
    ]
    
    # Если входной текст содержит ключевые слова, выбираем соответствующие результаты
    if "хорошо" in input_text or "успех" in input_text or "положительно" in input_text:
        result = possible_results[0]
    elif "плохо" in input_text or "неудача" in input_text or "отрицательно" in input_text:
        result = possible_results[1]
    else:
        # Случайный выбор результата, но с большей вероятностью неопределенного
        weights = [0.3, 0.3, 0.4]
        result = random.choices(possible_results, weights=weights, k=1)[0]
    
    # Добавляем дополнительную информацию в результат
    result["timestamp"] = datetime.now().isoformat()
    result["input_length"] = len(input_text)
    result["worker_id"] = WORKER_ID
    
    return {"result": result}

def save_prediction_result(user_id: int, input_data: Dict[str, Any], prediction_result: Dict[str, Any]) -> None:
    """
    Сохраняет результат предсказания в базу данных
    
    Args:
        user_id: ID пользователя
        input_data: Входные данные
        prediction_result: Результат предсказания
    """
    db = next(get_db_session())
    try:
        # Создание записи о предсказании
        prediction = Prediction(
            user_id=user_id,
            input_data=json.dumps(input_data),
            result=json.dumps(prediction_result),
            cost=PREDICTION_COST
        )
        db.add(prediction)
        
        # Создание транзакции на списание средств
        transaction = Transaction(
            user_id=user_id,
            amount=PREDICTION_COST,
            type="withdrawal",
            status="completed"
        )
        db.add(transaction)
        
        # Списание средств с баланса
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        if balance:
            balance.amount -= PREDICTION_COST
        
        db.commit()
        logger.info(f"Результат предсказания сохранен для пользователя {user_id} (воркер: {WORKER_ID})")
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сохранении результата: {e}")
    finally:
        db.close()

def process_message(ch, method, properties, body):
    """
    Обрабатывает входящее сообщение из очереди
    
    Args:
        ch: Канал RabbitMQ
        method: Информация о методе доставки
        properties: Свойства сообщения
        body: Тело сообщения
    """
    try:
        # Декодируем сообщение
        message = json.loads(body.decode('utf-8'))
        logger.info(f"Воркер {WORKER_ID} получил сообщение: {message}")
        
        # Валидируем данные
        if not validate_data(message):
            logger.error(f"Воркер {WORKER_ID}: сообщение не прошло валидацию")
            # Подтверждаем получение сообщения, даже если оно некорректное
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
            
        # Получаем необходимые данные из сообщения
        user_id = message["user_id"]
        input_data = message["input_data"]
        
        # Выполняем предсказание
        logger.info(f"Воркер {WORKER_ID}: начинаем обработку задачи для пользователя {user_id}")
        prediction_result = make_ml_prediction(input_data)
        
        # Сохраняем результат в базу данных
        save_prediction_result(user_id, input_data, prediction_result)
        
        # Подтверждаем обработку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Воркер {WORKER_ID}: задача успешно обработана")
    except Exception as e:
        logger.error(f"Воркер {WORKER_ID}: ошибка при обработке сообщения: {e}")
        # В случае ошибки, все равно подтверждаем сообщение, чтобы не зацикливаться
        ch.basic_ack(delivery_tag=method.delivery_tag)

def run_worker():
    """
    Запускает воркер для обработки ML задач
    """
    logger.info(f"Запуск ML воркера с идентификатором: {WORKER_ID}")
    
    # Бесконечный цикл для переподключения при ошибках
    while True:
        try:
            # Запускаем потребление сообщений
            logger.info(f"Воркер {WORKER_ID} подключается к RabbitMQ...")
            consume_messages(process_message, ML_TASK_QUEUE)
        except pika.exceptions.AMQPConnectionError:
            logger.error(f"Воркер {WORKER_ID}: ошибка подключения к RabbitMQ. Повторная попытка через 5 секунд...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Воркер {WORKER_ID}: непредвиденная ошибка: {e}. Повторная попытка через 10 секунд...")
            time.sleep(10)

if __name__ == "__main__":
    run_worker() 