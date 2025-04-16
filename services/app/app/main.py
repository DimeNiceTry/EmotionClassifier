"""
Точка входа в FastAPI приложение.
"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.app.app.services import init_db, wait_for_rabbitmq
from services.app.app.routers import user_router, prediction_router, transaction_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Регистрация маршрутов
app.include_router(user_router, prefix="/api")
app.include_router(prediction_router, prefix="/api/predictions")
app.include_router(transaction_router, prefix="/api")


@app.get("/")
async def root():
    """Корневой эндпоинт API."""
    return {"message": "ML Service API"}


@app.get("/health")
async def health_check():
    """Эндпоинт проверки работоспособности сервиса."""
    return {"status": "ok", "service": "ML Service API"}


@app.on_event("startup")
async def startup_event():
    """
    Действия при запуске сервиса.
    - Инициализация базы данных
    - Проверка подключения к RabbitMQ
    """
    logger.info("Запуск ML Service API")
    
    # Инициализация базы данных
    if not init_db():
        logger.error("Ошибка инициализации базы данных")
        sys.exit(1)
    
    # Проверка подключения к RabbitMQ
    if not wait_for_rabbitmq():
        logger.error("Ошибка подключения к RabbitMQ")
        sys.exit(1)
    
    logger.info("ML Service API успешно запущен") 