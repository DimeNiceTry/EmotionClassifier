"""
Pydantic схемы для предсказаний.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime


class PredictionRequest(BaseModel):
    """Схема запроса на предсказание."""
    data: Dict[str, Any]


class PredictionResponse(BaseModel):
    """Схема ответа с предсказанием."""
    prediction_id: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    cost: float

    class Config:
        orm_mode = True


class PredictionHistory(BaseModel):
    """Схема истории предсказаний."""
    predictions: List[PredictionResponse] 