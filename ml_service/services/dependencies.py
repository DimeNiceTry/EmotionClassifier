"""
Функции для инициализации зависимостей сервисов.
"""
import os
from fastapi import Depends
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..repositories.sqlalchemy_repositories import (
    SQLAlchemyUserRepository, 
    SQLAlchemyBalanceRepository,
    SQLAlchemyTransactionRepository,
    SQLAlchemyPredictionRepository
)
from .user_service import UserService
from .prediction_service import PredictionService
from .auth_service import AuthService

# Константы для сервисов
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
PREDICTION_COST = 1.0


def get_user_repository(db: Session = Depends(get_db)):
    return SQLAlchemyUserRepository(db)


def get_balance_repository(db: Session = Depends(get_db)):
    return SQLAlchemyBalanceRepository(db)


def get_transaction_repository(db: Session = Depends(get_db)):
    return SQLAlchemyTransactionRepository(db)


def get_prediction_repository(db: Session = Depends(get_db)):
    return SQLAlchemyPredictionRepository(db)


def get_user_service(
    user_repository = Depends(get_user_repository),
    balance_repository = Depends(get_balance_repository),
    transaction_repository = Depends(get_transaction_repository)
):
    return UserService(user_repository, balance_repository, transaction_repository)


def get_prediction_service(
    prediction_repository = Depends(get_prediction_repository),
    balance_repository = Depends(get_balance_repository),
    transaction_repository = Depends(get_transaction_repository)
):
    return PredictionService(
        prediction_repository, 
        balance_repository, 
        transaction_repository,
        PREDICTION_COST
    )


def get_auth_service(
    user_repository = Depends(get_user_repository)
):
    return AuthService(
        user_repository, 
        SECRET_KEY, 
        ALGORITHM, 
        ACCESS_TOKEN_EXPIRE_MINUTES
    ) 