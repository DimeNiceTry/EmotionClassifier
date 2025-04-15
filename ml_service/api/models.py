"""
Модели запросов и ответов для API.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# Аутентификация и пользователи
class Token(BaseModel):
    access_token: str
    token_type: str


class UserInfo(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


# Баланс и транзакции
class UserBalance(BaseModel):
    balance: float


class TransactionResponse(BaseModel):
    transaction_id: int
    amount: float
    type: str
    timestamp: datetime
    status: str


class TransactionHistory(BaseModel):
    transactions: List[TransactionResponse]


# Предсказания
class PredictionRequest(BaseModel):
    data: Dict[str, Any]


class PredictionResponse(BaseModel):
    prediction_id: int
    result: Dict[str, Any]
    timestamp: datetime
    cost: float


class PredictionHistory(BaseModel):
    predictions: List[PredictionResponse] 