"""
Инициализация FastAPI приложения.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    """Создание и конфигурация экземпляра FastAPI."""
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
    
    # Импортируем и регистрируем роуты
    from app.api.routes import auth, users, predictions, balance, healthcheck
    
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(predictions.router)
    app.include_router(balance.router)
    app.include_router(healthcheck.router)
    
    # События приложения
    from app.core.events import startup_event
    app.add_event_handler("startup", startup_event)
    
    return app 