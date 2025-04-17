"""
Сервис для работы с базой данных в ML Worker.
"""
import logging
import time
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import psycopg2

from ml_service.models.transactions.transaction import Transaction
from ml_service.models.base.entity import Entity
from worker.config.settings import DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, DATABASE_URL

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем движок SQLAlchemy для работы с PostgreSQL
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Возвращает сессию базы данных, закрывая её после использования.
    
    Returns:
        Session: Сессия SQLAlchemy для работы с БД
    """
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e


def wait_for_db():
    """
    Ожидает доступности базы данных.
    
    Returns:
        bool: True, если подключение успешно, иначе False
    """
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
                # Подключаемся к postgres для проверки доступности
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


def update_prediction_result(prediction_id, result):
    """
    Обновляет результат предсказания в базе данных.
    
    Args:
        prediction_id: ID предсказания
        result: Результат предсказания
        
    Returns:
        bool: True, если обновление прошло успешно, иначе False
    """
    db = None
    try:
        db = get_db()
        
        # Преобразуем результат в безопасный JSON
        result_json = None
        try:
            if isinstance(result, str):
                try:
                    json.loads(result)  # Проверка валидности
                    result_json = result
                except json.JSONDecodeError:
                    result_json = json.dumps({"raw_text": result})
            else:
                result_json = json.dumps(convert_to_safe_json(result))
        except Exception as e:
            logger.error(f"Ошибка сериализации результата в JSON: {e}")
            result_json = json.dumps({"error": "Ошибка формата результата", "details": str(e)})
        
        # Получаем предсказание из базы данных
        from ml_service.models.transactions.prediction import Prediction
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        
        if not prediction:
            logger.error(f"Предсказание с ID {prediction_id} не найдено")
            return False
        
        # Обновляем предсказание с использованием ORM
        prediction.result = result_json
        prediction.status = "completed"
        prediction.completed_at = datetime.now()
        
        db.commit()
        logger.info(f"Результат предсказания {prediction_id} сохранен в БД")
        return True
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Ошибка при обновлении результата предсказания: {e}")
        return False
    finally:
        if db:
            db.close()


def convert_to_safe_json(obj):
    """
    Преобразует объект в безопасный для JSON формат.
    
    Args:
        obj: Объект для преобразования
        
    Returns:
        Объект, безопасный для JSON сериализации
    """
    if isinstance(obj, dict):
        return {k: convert_to_safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_safe_json(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Преобразуем неподдерживаемые типы в строки
        return str(obj) 