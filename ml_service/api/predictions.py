from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
import json
from ..database.database import get_db
from ..database.models import User, Balance, Prediction, Transaction
from .auth import get_current_user
from ..rabbitmq.rabbitmq import publish_message

router = APIRouter()

class PredictionRequest(BaseModel):
    data: dict

class PredictionResponse(BaseModel):
    prediction_id: int
    result: dict
    timestamp: datetime
    cost: float

    class Config:
        from_attributes = True

class PredictionHistory(BaseModel):
    predictions: List[PredictionResponse]

PREDICTION_COST = 1.0  # Стоимость одного предсказания

@router.post("/predict", response_model=PredictionResponse)
async def make_prediction(
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверка баланса пользователя
    balance = db.query(Balance).filter(Balance.user_id == current_user.id).first()
    if not balance or balance.amount < PREDICTION_COST:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )
    
    # Создаем временную запись о предсказании с пустым результатом
    prediction = Prediction(
        user_id=current_user.id,
        input_data=json.dumps(request.data),
        result=json.dumps({"status": "pending"}),
        cost=PREDICTION_COST
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    
    # Отправляем задачу в очередь RabbitMQ
    message = {
        "user_id": current_user.id,
        "prediction_id": prediction.id,
        "input_data": request.data
    }
    
    try:
        publish_message(message)
        
        # Создаем ответ для клиента
        prediction_response = {
            "prediction_id": prediction.id,
            "result": {"status": "pending", "message": "Задача отправлена на обработку"},
            "timestamp": prediction.created_at,
            "cost": prediction.cost
        }
        
        return prediction_response
    except Exception as e:
        # В случае ошибки отправки, удаляем созданную запись
        db.delete(prediction)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue prediction task: {str(e)}"
        )

@router.get("/history", response_model=PredictionHistory)
async def get_prediction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    predictions = db.query(Prediction).filter(
        Prediction.user_id == current_user.id
    ).order_by(Prediction.created_at.desc()).all()
    
    # Создаем список предсказаний вручную
    prediction_list = []
    for p in predictions:
        try:
            result_dict = json.loads(p.result)
        except:
            result_dict = {"result": "Error parsing prediction result"}
        
        prediction_list.append({
            "prediction_id": p.id,
            "result": result_dict,
            "timestamp": p.created_at,
            "cost": p.cost
        })
    
    return PredictionHistory(predictions=prediction_list)

@router.get("/status/{prediction_id}")
async def get_prediction_status(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем существование предсказания и принадлежность текущему пользователю
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.user_id == current_user.id
    ).first()
    
    if not prediction:
        raise HTTPException(
            status_code=404,
            detail="Prediction not found"
        )
    
    try:
        result_dict = json.loads(prediction.result)
    except:
        result_dict = {"status": "error", "message": "Error parsing prediction result"}
    
    return {
        "prediction_id": prediction.id,
        "status": "completed" if "result" in result_dict else "pending",
        "result": result_dict,
        "timestamp": prediction.created_at,
        "cost": prediction.cost
    }

# Закомментированная функция, так как теперь мы используем RabbitMQ
# async def make_ml_prediction(data: dict) -> dict:
#     """
#     Выполняет предсказание на основе входных данных
#     
#     В реальном приложении здесь была бы настоящая модель машинного обучения.
#     Сейчас реализована простая имитация, которая генерирует различные ответы
#     в зависимости от входных данных.
#     """
#     import random
#     from datetime import datetime
#     
#     # Получаем текст запроса или используем пустую строку
#     input_text = data.get("text", "").lower() if isinstance(data, dict) else ""
#     
#     # Список возможных результатов предсказания
#     possible_results = [
#         {"prediction": "Положительный результат", "confidence": round(random.uniform(0.7, 0.95), 2)},
#         {"prediction": "Отрицательный результат", "confidence": round(random.uniform(0.6, 0.85), 2)},
#         {"prediction": "Неопределенный результат", "confidence": round(random.uniform(0.4, 0.6), 2)}
#     ]
#     
#     # Если входной текст содержит ключевые слова, выбираем соответствующие результаты
#     if "хорошо" in input_text or "успех" in input_text or "положительно" in input_text:
#         result = possible_results[0]
#     elif "плохо" in input_text or "неудача" in input_text or "отрицательно" in input_text:
#         result = possible_results[1]
#     else:
#         # Случайный выбор результата, но с большей вероятностью неопределенного
#         weights = [0.3, 0.3, 0.4]
#         result = random.choices(possible_results, weights=weights, k=1)[0]
#     
#     # Добавляем дополнительную информацию в результат
#     result["timestamp"] = datetime.now().isoformat()
#     result["input_length"] = len(input_text)
#     
#     return {"result": result} 