#!/usr/bin/env python3
"""
Точка входа для FastAPI приложения.
"""
import uvicorn
import logging

from app import create_app

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем экземпляр приложения
app = create_app()

if __name__ == "__main__":
    logger.info("Запуск приложения...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False) 