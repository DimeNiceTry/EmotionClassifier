import os
import logging
from ml_service.api.main import app

# Настройка логгирования
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ml_service")

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8080"))
    
    logger.info(f"Starting ML Service API at {host}:{port}")
    uvicorn.run("ml_service.api.main:app", host=host, port=port) 