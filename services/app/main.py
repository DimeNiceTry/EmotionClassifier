#!/usr/bin/env python3
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
import json
import uuid
import time
import pika
import logging
import uvicorn
from datetime import datetime, timedelta
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import random

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройки PostgreSQL
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
ML_TASK_QUEUE = "ml_tasks"
ML_RESULT_QUEUE = "ml_results"

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "secret_key_for_jwt")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Настройки ML
PREDICTION_COST = float(os.getenv("PREDICTION_COST", "1.0"))

# Создание FastAPI приложения
app = FastAPI(
    title="ML Service API",
    description="REST API для сервиса машинного обучения с системой оплаты предсказаний",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---

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

def create_database():
    """Создает базу данных и необходимые таблицы."""
    try:
        # Подключение к postgres для создания новой БД
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Проверяем, существует ли база данных
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Создаем базу данных {DB_NAME}...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"База данных {DB_NAME} успешно создана")
        else:
            logger.info(f"База данных {DB_NAME} уже существует")
        
        cursor.close()
        conn.close()
        
        # Подключаемся к новой базе данных и создаем таблицы
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME
        )
        cursor = conn.cursor()
        
        # Создаем таблицы
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255),
            password VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            amount DECIMAL(10, 2) DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id VARCHAR(36) PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            input_data JSONB NOT NULL,
            result JSONB,
            status VARCHAR(20) DEFAULT 'pending',
            cost DECIMAL(10, 2) DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            amount DECIMAL(10, 2) NOT NULL,
            type VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Создаем тестового пользователя, если его нет
        cursor.execute("SELECT 1 FROM users WHERE username = 'test'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                ("test", "test@example.com", "test")  # Для тестов, в реальном приложении хешировать пароль
            )
            user_id = cursor.fetchone()[0]
            
            # Добавляем баланс для тестового пользователя
            cursor.execute(
                "INSERT INTO balances (user_id, amount) VALUES (%s, %s)",
                (user_id, 100.0)
            )
        
        conn.commit()
        logger.info("Таблицы успешно созданы")
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании базы данных: {e}")
        return False

def init_db():
    """Инициализирует базу данных."""
    if wait_for_db():
        return create_database()
    return False

# --- СХЕМЫ ДАННЫХ ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class PredictionRequest(BaseModel):
    data: Dict[str, Any]

class PredictionResponse(BaseModel):
    prediction_id: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime
    cost: float

class PredictionHistory(BaseModel):
    predictions: List[PredictionResponse]

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С БД И RABBITMQ ---

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

def get_rabbitmq_connection():
    """Создает соединение с RabbitMQ"""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)

def publish_message(message, queue_name=ML_TASK_QUEUE):
    """Публикует сообщение в очередь RabbitMQ"""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Объявляем очередь как durable для сохранения сообщений при перезапуске RabbitMQ
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Публикуем сообщение
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message).encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=2,  # сообщение будет сохранено на диск
                content_type='application/json',
                correlation_id=str(uuid.uuid4())  # уникальный идентификатор сообщения
            )
        )
        
        connection.close()
        logger.info(f"Сообщение отправлено в очередь {queue_name}: {message.get('prediction_id', 'unknown')}")
        return True
    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"Ошибка соединения с RabbitMQ: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        return False

# --- АВТОРИЗАЦИЯ ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE username = %s", (token_data.username,))
    user_record = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user_record is None:
        raise credentials_exception
    
    return User(
        id=user_record["id"],
        username=user_record["username"],
        email=user_record["email"] if "email" in user_record else None,
        is_active=user_record["is_active"] if "is_active" in user_record else True
    )

# --- API ЭНДПОИНТЫ ---

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT * FROM users WHERE username = %s",
        (form_data.username,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user or user["password"] != form_data.password:  # В реальном приложении сравниваем хеши паролей
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users", response_model=User)
async def create_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Проверяем, существует ли пользователь
    cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Создаем пользователя
    cursor.execute(
        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id, username, email, is_active",
        (user.username, user.email, user.password)  # В реальном приложении хешируем пароль
    )
    new_user = cursor.fetchone()
    
    # Создаем начальный баланс
    cursor.execute(
        "INSERT INTO balances (user_id, amount) VALUES (%s, %s)",
        (new_user["id"], 10.0)  # Даем 10 кредитов новому пользователю
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return User(
        id=new_user["id"],
        username=new_user["username"],
        email=new_user["email"],
        is_active=new_user["is_active"]
    )

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/predictions/predict", response_model=PredictionResponse)
async def make_prediction(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Создает предсказание и отправляет задачу в очередь
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Проверяем баланс пользователя
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (current_user.id,))
        balance = cursor.fetchone()
        
        if not balance or balance["amount"] < PREDICTION_COST:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Недостаточно средств на балансе"
            )
        
        # Генерируем ID для предсказания
        prediction_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Записываем предсказание в БД
        cursor.execute(
            """
            INSERT INTO predictions (id, user_id, input_data, status, cost, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (prediction_id, current_user.id, json.dumps(request.data), "pending", PREDICTION_COST, timestamp)
        )
        
        # Списываем средства с баланса
        cursor.execute(
            """
            UPDATE balances
            SET amount = amount - %s, updated_at = %s
            WHERE user_id = %s
            """,
            (PREDICTION_COST, timestamp, current_user.id)
        )
        
        # Записываем транзакцию
        cursor.execute(
            """
            INSERT INTO transactions (user_id, amount, type, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (current_user.id, -PREDICTION_COST, "prediction", "completed", timestamp)
        )
        
        conn.commit()
        
        # Формируем сообщение для очереди
        message = {
            "prediction_id": prediction_id,
            "user_id": current_user.id,
            "data": request.data,
            "timestamp": timestamp.isoformat()
        }
        
        # Отправляем сообщение в очередь
        if not publish_message(message):
            # Обработка ошибки отправки
            logger.error(f"Не удалось отправить задание в очередь для предсказания {prediction_id}")
            
            # Восстанавливаем баланс и помечаем предсказание как failed
            cursor.execute(
                """
                UPDATE predictions
                SET status = %s
                WHERE id = %s
                """,
                ("failed", prediction_id)
            )
            
            cursor.execute(
                """
                UPDATE balances
                SET amount = amount + %s, updated_at = %s
                WHERE user_id = %s
                """,
                (PREDICTION_COST, datetime.now(), current_user.id)
            )
            
            cursor.execute(
                """
                INSERT INTO transactions (user_id, amount, type, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (current_user.id, PREDICTION_COST, "refund", "completed", datetime.now())
            )
            
            conn.commit()
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Сервис ML временно недоступен"
            )
        
        cursor.close()
        conn.close()
        
        return PredictionResponse(
            prediction_id=prediction_id,
            status="pending",
            timestamp=timestamp,
            cost=PREDICTION_COST
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании предсказания: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )

@app.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    current_user: User = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT * FROM predictions 
        WHERE id = %s AND user_id = %s
        """,
        (prediction_id, current_user.id)
    )
    prediction = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    result = json.loads(prediction["result"]) if prediction["result"] else None
    
    return PredictionResponse(
        prediction_id=prediction["id"],
        status=prediction["status"],
        result=result,
        timestamp=prediction["created_at"],
        cost=prediction["cost"]
    )

@app.get("/predictions", response_model=PredictionHistory)
async def get_predictions(
    current_user: User = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute(
        """
        SELECT * FROM predictions 
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (current_user.id,)
    )
    predictions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    prediction_responses = []
    for prediction in predictions:
        result = json.loads(prediction["result"]) if prediction["result"] else None
        prediction_responses.append(
            PredictionResponse(
                prediction_id=prediction["id"],
                status=prediction["status"],
                result=result,
                timestamp=prediction["created_at"],
                cost=prediction["cost"]
            )
        )
    
    return PredictionHistory(predictions=prediction_responses)

@app.get("/balance")
async def get_balance(current_user: User = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (current_user.id,))
    balance = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")
    
    return {"balance": balance["amount"]}

@app.get("/")
async def root():
    return {"message": "ML Service API"}

@app.get("/health")
async def health_check():
    """Эндпоинт для проверки работоспособности сервиса."""
    return {"status": "healthy"}

# Запуск инициализации базы данных при старте приложения
@app.on_event("startup")
async def startup_event():
    logger.info("Инициализация приложения...")
    init_db()
    logger.info("Приложение готово к работе")

# Если запускается напрямую через Python
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 