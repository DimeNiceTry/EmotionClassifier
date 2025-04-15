"""
Доменные модели - основные бизнес-сущности приложения.
В отличие от моделей БД, эти модели не зависят от конкретной реализации хранения данных.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PAYMENT = "payment"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    hashed_password: Optional[str] = None


class UserBalance(BaseModel):
    user_id: int
    amount: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Transaction(BaseModel):
    id: Optional[int] = None
    user_id: int
    amount: float
    type: TransactionType
    status: TransactionStatus = TransactionStatus.COMPLETED
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PredictionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PredictionInput(BaseModel):
    data: Dict[str, Any]


class PredictionResult(BaseModel):
    result: Dict[str, Any] = Field(default_factory=dict)
    status: PredictionStatus = PredictionStatus.PENDING


class Prediction(BaseModel):
    id: Optional[int] = None
    user_id: int
    input_data: Dict[str, Any]
    result: PredictionResult
    cost: float
    created_at: datetime = Field(default_factory=datetime.utcnow) 