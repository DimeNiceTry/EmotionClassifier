"""
Сервис для работы с предсказаниями ML моделей.
"""
from typing import List, Optional, Dict, Any
from ..domain.models import (
    Prediction, PredictionInput, PredictionResult, 
    PredictionStatus, Transaction, TransactionType
)
from ..repositories.interfaces import PredictionRepository, BalanceRepository, TransactionRepository
from ..rabbitmq.rabbitmq import publish_message


class PredictionService:
    def __init__(
        self, 
        prediction_repository: PredictionRepository,
        balance_repository: BalanceRepository,
        transaction_repository: TransactionRepository,
        prediction_cost: float = 1.0
    ):
        self.prediction_repository = prediction_repository
        self.balance_repository = balance_repository
        self.transaction_repository = transaction_repository
        self.prediction_cost = prediction_cost
    
    async def create_prediction(self, user_id: int, prediction_input: PredictionInput) -> Prediction:
        """
        Создать новое предсказание и отправить задачу в очередь.
        """
        # Проверка баланса пользователя
        balance = await self.balance_repository.get_by_user_id(user_id)
        if not balance or balance.amount < self.prediction_cost:
            raise ValueError("Insufficient balance")
        
        # Создаем запись о предсказании
        prediction = Prediction(
            user_id=user_id,
            input_data=prediction_input.data,
            result=PredictionResult(
                status=PredictionStatus.PENDING,
                result={"status": "pending", "message": "Prediction task is queued"}
            ),
            cost=self.prediction_cost
        )
        
        prediction = await self.prediction_repository.create(prediction)
        
        # Отправляем задачу в очередь RabbitMQ
        message = {
            "user_id": user_id,
            "prediction_id": prediction.id,
            "input_data": prediction_input.data
        }
        
        try:
            publish_message(message)
            
            # Списываем средства с баланса пользователя
            balance.amount -= self.prediction_cost
            await self.balance_repository.update(balance)
            
            # Создаем транзакцию
            transaction = Transaction(
                user_id=user_id,
                amount=self.prediction_cost,
                type=TransactionType.PAYMENT,
                status="completed"
            )
            await self.transaction_repository.create(transaction)
            
            return prediction
        except Exception as e:
            # В случае ошибки, удаляем предсказание
            # В реальном приложении здесь должна быть транзакция
            raise ValueError(f"Failed to queue prediction task: {str(e)}")
    
    async def get_prediction_by_id(self, prediction_id: int, user_id: int) -> Optional[Prediction]:
        """
        Получить предсказание по ID и проверить права доступа.
        """
        prediction = await self.prediction_repository.get_by_id(prediction_id)
        if not prediction or prediction.user_id != user_id:
            return None
        return prediction
    
    async def get_user_predictions(self, user_id: int) -> List[Prediction]:
        """
        Получить все предсказания пользователя.
        """
        return await self.prediction_repository.get_by_user_id(user_id)
    
    async def update_prediction_result(self, prediction_id: int, result: Dict[str, Any]) -> Prediction:
        """
        Обновить результат предсказания.
        """
        prediction = await self.prediction_repository.get_by_id(prediction_id)
        if not prediction:
            raise ValueError(f"Prediction with id {prediction_id} not found")
        
        # Обновляем результат
        prediction.result.result = result
        prediction.result.status = PredictionStatus.COMPLETED
        
        return await self.prediction_repository.update(prediction) 