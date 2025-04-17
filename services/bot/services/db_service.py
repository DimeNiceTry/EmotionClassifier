"""
Сервис для работы с базой данных.
"""
import os
import logging
import time
import psycopg2
from psycopg2.extras import RealDictCursor

# Настройка логирования
logger = logging.getLogger(__name__)

# Настройки PostgreSQL
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

def get_db_connection():
    """
    Создает соединение с базой данных.
    
    Returns:
        psycopg2.connection: Соединение с базой данных
    """
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

def wait_for_db():
    """
    Ожидает доступности базы данных.
    
    Returns:
        bool: True если подключение успешно, False в случае ошибки
    """
    retry_count = 0
    max_retries = 30
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к PostgreSQL (попытка {retry_count + 1}/{max_retries})...")
            conn = get_db_connection()
            logger.info("Подключение к PostgreSQL успешно установлено")
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к PostgreSQL после нескольких попыток")
    return False

async def register_user(telegram_id, username):
    """
    Регистрирует пользователя в системе.
    
    Args:
        telegram_id: ID пользователя в Telegram
        username: Имя пользователя в Telegram
        
    Returns:
        int: ID пользователя в базе данных
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{telegram_id}",))
        user = cursor.fetchone()
        
        if not user:
            # Создаем нового пользователя
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                (f"tg_{telegram_id}", f"{username}@telegram.org", f"tg_pass_{telegram_id}")
            )
            user_id = cursor.fetchone()["id"]
            
            # Создаем баланс для пользователя
            cursor.execute(
                "INSERT INTO balances (user_id, amount) VALUES (%s, %s)",
                (user_id, 10.0)  # Даем 10 кредитов новому пользователю
            )
            
            conn.commit()
            logger.info(f"Зарегистрирован новый пользователь: {username} (ID: {telegram_id})")
            return user_id
        else:
            logger.info(f"Пользователь уже существует: {username} (ID: {telegram_id})")
            return user["id"]
    
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        if conn:
            conn.rollback()
        raise
    
    finally:
        if conn:
            conn.close()

async def get_user_balance(user_id):
    """
    Получает баланс пользователя.
    
    Args:
        user_id: ID пользователя в базе данных
        
    Returns:
        float: Баланс пользователя
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (user_id,))
        balance = cursor.fetchone()
        
        if not balance:
            return 0.0
        
        return float(balance[0])
    
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        raise
    
    finally:
        if conn:
            conn.close() 