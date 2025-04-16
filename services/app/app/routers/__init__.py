"""
Роутеры FastAPI.
"""
from services.app.app.routers.user_router import router as user_router
from services.app.app.routers.prediction_router import router as prediction_router
from services.app.app.routers.transaction_router import router as transaction_router

__all__ = ["user_router", "prediction_router", "transaction_router"] 