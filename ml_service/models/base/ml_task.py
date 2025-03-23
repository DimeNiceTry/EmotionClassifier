"""
Абстрактный класс для задач машинного обучения.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class MLTask(ABC):
    """Абстрактный класс для задач машинного обучения."""

    @abstractmethod
    def validate_data(self, data: Any) -> Dict[str, Any]:
        """
        Валидация входных данных.
        
        Args:
            data: Входные данные для анализа
            
        Returns:
            Словарь с валидными данными и ошибками
        """
        pass

    @abstractmethod
    def predict(self, validated_data: Any) -> Any:
        """
        Выполнить предсказание на основе валидированных данных.
        
        Args:
            validated_data: Валидированные данные
            
        Returns:
            Результат предсказания
        """
        pass

    @abstractmethod
    def get_cost(self) -> int:
        """
        Получить стоимость выполнения задачи в кредитах.
        
        Returns:
            Стоимость в кредитах
        """
        pass 