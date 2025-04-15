from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from ..services.dependencies import get_prediction_service
from ..services.prediction_service import PredictionService
from ..domain.models import User, PredictionInput, Prediction as PredictionDomain
from .auth import get_current_user
from .models import PredictionRequest, PredictionResponse, PredictionHistory

router = APIRouter()

@router.post("/predict", response_model=PredictionResponse)
async def make_prediction(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    try:
        # Преобразуем входные данные в доменную модель
        prediction_input = PredictionInput(data=request.data)
        
        # Создаем предсказание через сервис
        prediction = await prediction_service.create_prediction(current_user.id, prediction_input)
        
        # Возвращаем результат
        return PredictionResponse(
            prediction_id=prediction.id,
            result=prediction.result.result,
            timestamp=prediction.created_at,
            cost=prediction.cost
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history", response_model=PredictionHistory)
async def get_prediction_history(
    current_user: User = Depends(get_current_user),
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    # Получаем все предсказания пользователя через сервис
    predictions = await prediction_service.get_user_predictions(current_user.id)
    
    # Преобразуем доменные модели в DTO для ответа
    prediction_responses = [
        PredictionResponse(
            prediction_id=p.id,
            result=p.result.result,
            timestamp=p.created_at,
            cost=p.cost
        ) for p in predictions
    ]
    
    return PredictionHistory(predictions=prediction_responses)

@router.get("/status/{prediction_id}")
async def get_prediction_status(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    # Получаем предсказание через сервис
    prediction = await prediction_service.get_prediction_by_id(prediction_id, current_user.id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    # Формируем ответ
    return {
        "prediction_id": prediction.id,
        "status": prediction.result.status.value,
        "result": prediction.result.result,
        "timestamp": prediction.created_at,
        "cost": prediction.cost
    } 