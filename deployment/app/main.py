import os
import logging
from typing import Dict
import uvicorn
from fastapi import FastAPI

# Настройка логгирования
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ml_service")

# Создание экземпляра приложения
app = FastAPI(title="ML Service API", version="0.1.0")

@app.get("/")
async def root() -> Dict[str, str]:
    """Корневой эндпоинт."""
    return {"message": "ML Service API is up and running"}

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Эндпоинт для проверки работоспособности."""
    return {"status": "healthy"}

if __name__ == "__main__":
    # Получение параметров из переменных окружения
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8080"))
    
    logger.info(f"Starting ML Service API at {host}:{port}")
    uvicorn.run(app, host=host, port=port) 