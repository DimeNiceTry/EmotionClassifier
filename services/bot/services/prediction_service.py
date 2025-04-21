"""
Сервис для работы с предсказаниями.
"""
import os
import uuid
import json
import logging
from datetime import datetime
import asyncio

from .db_service import get_db_connection, get_db_user_id
from .db_service import Session, Balance, Transaction
from .rabbitmq_service import publish_message, ML_TASK_QUEUE

# Настройка логирования
logger = logging.getLogger(__name__)

# Стоимость предсказания
PREDICTION_COST = float(os.getenv("PREDICTION_COST", "1.0"))

async def create_prediction(telegram_id, text):
    """
    Создает новое предсказание.
    
    Args:
        telegram_id: ID пользователя в Telegram
        text: Текст для предсказания
        
    Returns:
        str: ID созданного предсказания
    """
    conn = None
    session = None
    try:
        # Получаем внутренний ID пользователя
        db_user_id = await get_db_user_id(telegram_id)
        if not db_user_id:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            raise ValueError("Пользователь не найден. Используйте /start для регистрации.")
        
        logger.info(f"Создание предсказания для пользователя с Telegram ID {telegram_id} (DB_ID: {db_user_id})")
        
        # Генерируем уникальный ID
        prediction_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Подготавливаем сообщение для отправки в RabbitMQ
        message = {
            "prediction_id": prediction_id,
            "user_id": db_user_id,
            "data": {"text": text},
            "timestamp": now.isoformat()
        }
        
        # Проверяем баланс через SQLAlchemy
        session = Session()
        balance = session.query(Balance).filter(Balance.user_id == db_user_id).first()
        
        if not balance or balance.amount < PREDICTION_COST:
            logger.error(f"Недостаточно средств на балансе пользователя {db_user_id}: {balance.amount if balance else 0}")
            raise ValueError("Недостаточно средств на балансе")
        
        # Получаем соединение с БД для старого кода
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Обновляем баланс через SQLAlchemy
        balance.amount -= PREDICTION_COST
        
        # Создаем запись о транзакции через SQLAlchemy
        transaction = Transaction(
            user_id=db_user_id, 
            amount=PREDICTION_COST, 
            type="deduction", 
            status="completed"
        )
        session.add(transaction)
        
        # Создаем запись о предсказании
        cursor.execute(
            """
            INSERT INTO predictions 
            (id, user_id, input_data, status, cost, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (prediction_id, db_user_id, json.dumps({"text": text}), "pending", PREDICTION_COST, now)
        )
        
        # Отправляем сообщение в очередь
        if not publish_message(message, ML_TASK_QUEUE):
            conn.rollback()
            session.rollback()
            logger.error(f"Не удалось отправить сообщение в очередь для предсказания {prediction_id}")
            raise Exception("Ошибка при отправке задачи")
        
        # Подтверждаем транзакции
        conn.commit()
        session.commit()
        
        logger.info(f"Предсказание {prediction_id} успешно создано для пользователя {db_user_id}")
        return prediction_id
    
    except Exception as e:
        if conn:
            conn.rollback()
        if session:
            session.rollback()
        logger.error(f"Ошибка при создании предсказания: {e}")
        raise
    
    finally:
        if conn:
            conn.close()
        if session:
            session.close()

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

async def get_user_predictions(telegram_id, limit=5):
    """
    Получает список предсказаний пользователя.
    
    Args:
        telegram_id: ID пользователя в Telegram
        limit: Максимальное количество предсказаний
        
    Returns:
        list: Список предсказаний
    """
    conn = None
    try:
        # Получаем внутренний ID пользователя
        db_user_id = await get_db_user_id(telegram_id)
        if not db_user_id:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            raise ValueError("Пользователь не найден. Используйте /start для регистрации.")
        
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
            (db_user_id, limit)
        )
        predictions = cursor.fetchall()
        
        # Формируем результат
        result = []
        for p in predictions:
            # Обрабатываем поле result корректно, проверяя его тип
            result_data = None
            if p[2]:
                if isinstance(p[2], str):
                    try:
                        result_data = json.loads(p[2])
                    except json.JSONDecodeError:
                        result_data = {"prediction": "Error parsing result"}
                elif isinstance(p[2], dict):
                    result_data = p[2]
                else:
                    result_data = {"prediction": str(p[2])}
            
            result.append({
                "prediction_id": p[0],
                "status": p[1],
                "result": result_data,
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