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
        allow_origins=["http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Импортируем и регистрируем маршруты только из одного места
    from app.api.routes import auth, users, predictions, balance, healthcheck
    
    # Регистрируем маршруты с единым префиксом
    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(predictions.router, prefix="/api")
    app.include_router(balance.router, prefix="/api")
    app.include_router(healthcheck.router)
    
    # Добавляем тестовый маршрут для проверки
    @app.get("/api/test")
    async def test_endpoint():
        return {"status": "ok", "message": "API endpoint is working!"}
    
    return app 