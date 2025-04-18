"""
Модуль для обработки сообщений из очереди.
"""
import json
import logging
from sqlalchemy.orm import Session

from ml_service.models import Prediction
from services.ml_worker.worker.services.prediction_service import (
    validate_data,
    make_prediction,
    update_prediction_result
)
from services.ml_worker.worker.services.rabbitmq_service import publish_result

logger = logging.getLogger(__name__)

def process_message(ch, method, properties, body, worker_id, db):
    """
    Обрабатывает сообщение из очереди.
    
    Args:
        ch: Канал RabbitMQ
        method: Метод доставки сообщения
        properties: Свойства сообщения
        body: Тело сообщения
        worker_id: Идентификатор ML-воркера
        db: Сессия базы данных
    """
    try:
        # Разбираем сообщение
        data = json.loads(body)
        logger.info(f"Получено сообщение: {data}")
        
        # Валидируем данные
        if not validate_data(data):
            logger.error("Валидация данных не пройдена")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        # Извлекаем необходимые данные
        prediction_id = data["prediction_id"]
        user_id = data["user_id"]
        input_data = data["data"]
        
        # Выполняем предсказание
        logger.info(f"Выполняем предсказание для {prediction_id}")
        prediction_result = make_prediction(input_data)
        
        # Обновляем результат в базе данных
        update_prediction_result(db, prediction_id, prediction_result, worker_id)
        
        # Публикуем результат в очередь
        publish_result(prediction_id, prediction_result)
        
        logger.info(f"Предсказание {prediction_id} успешно обработано")
        
        # Подтверждаем обработку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        # Подтверждаем сообщение даже в случае ошибки
        # В реальном приложении можно использовать стратегию повторных попыток
        ch.basic_ack(delivery_tag=method.delivery_tag) 