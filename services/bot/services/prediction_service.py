"""
Сервис для работы с предсказаниями.
"""
import os
import uuid
import json
import logging
from datetime import datetime
import asyncio

from services.bot.services.db_service import get_db_connection
from services.bot.services.rabbitmq_service import publish_message, ML_TASK_QUEUE

# Настройка логирования
logger = logging.getLogger(__name__)

# Стоимость предсказания
PREDICTION_COST = float(os.getenv("PREDICTION_COST", "1.0"))

async def create_prediction(user_id, text):
    """
    Создает новое предсказание.
    
    Args:
        user_id: ID пользователя
        text: Текст для предсказания
        
    Returns:
        str: ID созданного предсказания
    """
    conn = None
    try:
        # Генерируем уникальный ID
        prediction_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Подготавливаем сообщение для отправки в RabbitMQ
        message = {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "data": {"text": text},
            "timestamp": now.isoformat()
        }
        
        # Получаем соединение с БД
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Списываем средства с баланса
        # 1. Проверяем баланс
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (user_id,))
        balance_row = cursor.fetchone()
        
        if not balance_row or float(balance_row[0]) < PREDICTION_COST:
            raise ValueError("Недостаточно средств на балансе")
        
        # 2. Обновляем баланс
        cursor.execute(
            "UPDATE balances SET amount = amount - %s WHERE user_id = %s",
            (PREDICTION_COST, user_id)
        )
        
        # 3. Создаем запись о транзакции
        cursor.execute(
            """
            INSERT INTO transactions 
            (user_id, amount, type, status, description, related_entity_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, PREDICTION_COST, "deduction", "completed", 
             f"Оплата предсказания #{prediction_id}", prediction_id)
        )
        
        # 4. Создаем запись о предсказании
        cursor.execute(
            """
            INSERT INTO predictions 
            (id, user_id, input_data, status, cost, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (prediction_id, user_id, json.dumps({"text": text}), "pending", PREDICTION_COST, now)
        )
        
        # Отправляем сообщение в очередь
        if not publish_message(message, ML_TASK_QUEUE):
            conn.rollback()
            logger.error(f"Не удалось отправить сообщение в очередь для предсказания {prediction_id}")
            raise Exception("Ошибка при отправке задачи")
        
        # Подтверждаем транзакцию
        conn.commit()
        
        return prediction_id
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Ошибка при создании предсказания: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

async def get_prediction_status(prediction_id):
    """
    Получает статус предсказания.
    
    Args:
        prediction_id: ID предсказания
        
    Returns:
        dict: Информация о предсказании
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, status, result, created_at, completed_at, cost 
            FROM predictions 
            WHERE id = %s
            """,
            (prediction_id,)
        )
        prediction = cursor.fetchone()
        
        if not prediction:
            raise ValueError(f"Предсказание {prediction_id} не найдено")
        
        # Формируем ответ
        result = {
            "prediction_id": prediction[0],
            "status": prediction[1],
            "result": json.loads(prediction[2]) if prediction[2] else None,
            "created_at": prediction[3],
            "completed_at": prediction[4],
            "cost": float(prediction[5])
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении статуса предсказания: {e}")
        raise
    
    finally:
        if conn:
            conn.close()

async def get_user_predictions(user_id, limit=5):
    """
    Получает список предсказаний пользователя.
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество предсказаний
        
    Returns:
        list: Список предсказаний
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, status, result, created_at, completed_at, cost 
            FROM predictions 
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit)
        )
        predictions = cursor.fetchall()
        
        # Формируем результат
        result = []
        for p in predictions:
            result.append({
                "prediction_id": p[0],
                "status": p[1],
                "result": json.loads(p[2]) if p[2] else None,
                "created_at": p[3],
                "completed_at": p[4],
                "cost": float(p[5])
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка предсказаний: {e}")
        raise
    
    finally:
        if conn:
            conn.close() 