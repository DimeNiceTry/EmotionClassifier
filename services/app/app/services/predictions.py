"""
Сервис для работы с предсказаниями ML.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config.settings import PREDICTION_COST
from app.services.rabbitmq import publish_message, ML_TASK_QUEUE
from app.services.transactions import deduct_from_balance
from ml_service.models.transactions.prediction import Prediction

# Настройка логирования
logger = logging.getLogger(__name__)


def create_prediction(db: Session, user_id: int, data: Dict[str, Any], cost: float = 1.0) -> Prediction:
    """
    Создает новую запись предсказания.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        data: Входные данные для предсказания
        cost: Стоимость предсказания
        
    Returns:
        Объект предсказания
    """
    prediction_id = str(uuid.uuid4())
    prediction = Prediction(
        id=prediction_id,
        user_id=user_id,
        input_data=data,
        status="pending",
        cost=cost
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def get_prediction_by_id(db: Session, prediction_id: str) -> Optional[Prediction]:
    """
    Получает предсказание по ID.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        
    Returns:
        Объект предсказания или None
    """
    return db.query(Prediction).filter(Prediction.id == prediction_id).first()


def get_user_predictions(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Prediction]:
    """
    Получает список предсказаний пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Смещение для пагинации
        limit: Ограничение количества результатов
        
    Returns:
        Список объектов предсказаний
    """
    return db.query(Prediction).filter(
        Prediction.user_id == user_id
    ).order_by(
        Prediction.created_at.desc()
    ).offset(skip).limit(limit).all()


def update_prediction_result(
    db: Session, 
    prediction_id: str, 
    result: Dict[str, Any], 
    worker_id: str
) -> Optional[Prediction]:
    """
    Обновляет результат предсказания.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        result: Результат предсказания
        worker_id: ID воркера, выполнившего предсказание
        
    Returns:
        Обновленный объект предсказания или None
    """
    prediction = get_prediction_by_id(db, prediction_id)
    if not prediction:
        return None
        
    prediction.result = result
    prediction.status = "completed"
    prediction.completed_at = datetime.utcnow()
    prediction.processed_by = worker_id
    
    db.commit()
    db.refresh(prediction)
    return prediction


def get_prediction(db: Session, prediction_id: str, user_id: str):
    """
    Получает информацию о предсказании.
    
    Args:
        db: Сессия базы данных
        prediction_id: ID предсказания
        user_id: ID пользователя (для проверки доступа)
        
    Returns:
        dict: Информация о предсказании
        
    Raises:
        ValueError: Если предсказание не найдено или не принадлежит пользователю
    """
    # Используем ORM для получения предсказания
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    
    if not prediction:
        raise ValueError("Предсказание не найдено")
    
    # Проверяем, принадлежит ли предсказание пользователю
    if prediction.user_id != user_id:
        raise ValueError("У вас нет доступа к этому предсказанию")
    
    # Форматируем ответ
    return {
        "prediction_id": prediction.id,
        "status": prediction.status,
        "result": prediction.result,
        "timestamp": prediction.created_at,
        "completed_at": prediction.completed_at,
        "cost": float(prediction.cost)
    }


def get_user_predictions_list(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    """
    Получает список предсказаний пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Количество записей для пропуска
        limit: Максимальное количество возвращаемых записей
        
    Returns:
        List[dict]: Список предсказаний
    """
    # Используем ORM для получения списка предсказаний
    predictions_query = db.query(Prediction).filter(
        Prediction.user_id == user_id
    ).order_by(
        Prediction.created_at.desc()
    ).offset(skip).limit(limit)
    
    predictions_list = []
    for prediction in predictions_query:
        # Форматируем ответ
        predictions_list.append({
            "prediction_id": prediction.id,
            "status": prediction.status,
            "result": prediction.result,
            "timestamp": prediction.created_at,
            "completed_at": prediction.completed_at,
            "cost": float(prediction.cost)
        })
    
    return predictions_list 