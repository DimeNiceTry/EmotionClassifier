from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth import router as auth_router
from .predictions import router as predictions_router
from .users import router as users_router
from ..database.init_db import init_db
import os
import uvicorn
import logging

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ml_service")

# Инициализация базы данных
init_db()

app = FastAPI(
    title="ML Service API",
    description="API для взаимодействия с ML сервисом",
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

# Включаем роутеры
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(predictions_router, prefix="/predictions", tags=["predictions"])
app.include_router(users_router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Welcome to ML Service API"}

@app.get("/health")
async def health_check():
    """Эндпоинт для проверки работоспособности сервиса."""
    return {"status": "healthy"}

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8080"))
    
    logger.info(f"Starting ML Service API at {host}:{port}")
    uvicorn.run(app, host=host, port=port) 