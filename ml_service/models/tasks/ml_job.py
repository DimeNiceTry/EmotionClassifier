"""
Модель работы (задачи) машинного обучения.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from ml_service.models.base.entity import Entity
from ml_service.models.base.ml_task import MLTask


class MLJob(Entity):
    """Модель работы (задачи) машинного обучения."""

    def __init__(
        self, 
        user_id: str, 
        task: MLTask, 
        input_data: Any,
        status: str = "pending",
        id: str = None
    ):
        super().__init__(id)
        self._user_id = user_id
        self._task = task
        self._input_data = input_data
        self._status = status  # pending, processing, completed, failed
        self._result = None
        self._error_message = None
        self._start_time = None
        self._end_time = None
        self._cost = task.get_cost()

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def task(self) -> MLTask:
        return self._task

    @property
    def input_data(self) -> Any:
        return self._input_data

    @property
    def status(self) -> str:
        return self._status

    @property
    def result(self) -> Optional[Any]:
        return self._result

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def start_time(self) -> Optional[datetime]:
        return self._start_time

    @property
    def end_time(self) -> Optional[datetime]:
        return self._end_time

    @property
    def cost(self) -> int:
        return self._cost

    @property
    def duration(self) -> Optional[float]:
        """
        Получить длительность выполнения задачи в секундах.
        
        Returns:
            Длительность в секундах или None, если задача не завершена
        """
        if self._start_time and self._end_time:
            return (self._end_time - self._start_time).total_seconds()
        return None

    def mark_as_processing(self) -> None:
        """Отметить задачу как выполняющуюся."""
        self._status = "processing"
        self._start_time = datetime.now()
        self.update()

    def mark_as_completed(self, result: Any) -> None:
        """
        Отметить задачу как успешно завершенную.
        
        Args:
            result: Результат выполнения задачи
        """
        self._status = "completed"
        self._result = result
        self._end_time = datetime.now()
        self.update()

    def mark_as_failed(self, error_message: str) -> None:
        """
        Отметить задачу как завершенную с ошибкой.
        
        Args:
            error_message: Сообщение об ошибке
        """
        self._status = "failed"
        self._error_message = error_message
        self._end_time = datetime.now()
        self.update()

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать задачу в словарь для сериализации.
        
        Returns:
            Словарь с данными задачи
        """
        return {
            'id': self.id,
            'user_id': self._user_id,
            'task_type': self._task.__class__.__name__,
            'status': self._status,
            'cost': self._cost,
            'result': self._result,
            'error_message': self._error_message,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'end_time': self._end_time.isoformat() if self._end_time else None,
            'duration': self.duration,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 