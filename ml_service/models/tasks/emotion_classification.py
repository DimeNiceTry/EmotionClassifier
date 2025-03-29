"""
Задача классификации эмоций человека.
"""
from typing import List, Dict, Any
import numpy as np
from datetime import datetime

from ml_service.models.base.ml_task import MLTask


class EmotionClassificationTask(MLTask):
    """Задача классификации эмоций человека."""

    # Список поддерживаемых эмоций
    SUPPORTED_EMOTIONS = [
        'anger', 'disgust', 'fear', 'happiness', 
        'sadness', 'surprise', 'neutral'
    ]

    # Стоимость выполнения одного запроса на классификацию
    COST_PER_REQUEST = 10

    def __init__(self, model_version: str = "1.0.0"):
        self._model_version = model_version
        # В реальной системе здесь будет инициализация модели машинного обучения

    @property
    def model_version(self) -> str:
        return self._model_version

    def validate_data(self, data: Any) -> Dict[str, Any]:
        """
        Валидация входных данных для классификации эмоций.
        
        Args:
            data: Входные данные (изображение)
            
        Returns:
            Словарь с валидными данными и ошибками
        """
        valid_data = []
        errors = []
        
        # Если данные представлены в виде списка, обрабатываем каждый элемент
        items = data if isinstance(data, list) else [data]
        
        for i, item in enumerate(items):
            # Проверка наличия данных
            if not item:
                errors.append(f"Item {i}: Empty data")
                continue
                
            # Проверка формата данных (в этом примере просто проверяем,
            # что присутствует поле 'image' или 'audio')
            if not ('image' in item or 'audio' in item):
                errors.append(f"Item {i}: Missing required 'image' or 'audio' field")
                continue
            
            valid_data.append(item)
        
        return {
            'valid_data': valid_data,
            'errors': errors
        }

    def predict(self, validated_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Выполнить предсказание эмоций на основе валидированных данных.
        
        Args:
            validated_data: Список валидированных данных
            
        Returns:
            Список предсказаний эмоций
        """
        results = []
        
        for item in validated_data:
            # В реальной системе здесь будет обращение к модели классификации эмоций
            # Для примера генерируем случайные предсказания
            predictions = {}
            for emotion in self.SUPPORTED_EMOTIONS:
                # Генерируем случайную вероятность для каждой эмоции
                predictions[emotion] = np.random.random()
            
            # Нормализуем вероятности, чтобы их сумма была равна 1
            total = sum(predictions.values())
            for emotion in predictions:
                predictions[emotion] /= total
            
            # Находим наиболее вероятную эмоцию
            dominant_emotion = max(predictions, key=predictions.get)
            
            results.append({
                'dominant_emotion': dominant_emotion,
                'probabilities': predictions,
                'timestamp': datetime.now().isoformat()
            })
        
        return results

    def get_cost(self) -> int:
        """
        Получить стоимость выполнения задачи в кредитах.
        
        Returns:
            Стоимость в кредитах
        """
        return self.COST_PER_REQUEST 