"""
Схемы данных для Pydantic, связанные с транзакциями.
"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class BalanceInfo(BaseModel):
    """Информация о балансе пользователя"""
    user_id: str
    amount: float
    updated_at: datetime

    class Config:
        orm_mode = True


class BalanceTopUpRequest(BaseModel):
    """Запрос на пополнение баланса"""
    amount: float


class BalanceTopUpResponse(BaseModel):
    """Ответ на запрос пополнения баланса"""
    previous_balance: float
    current_balance: float
    transaction_id: str 