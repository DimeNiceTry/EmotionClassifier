"""
Сервис для работы с моделями машинного обучения.
"""
import logging
import time
import random
from datetime import datetime
from typing import Dict, Any

from worker.config.settings import WORKER_ID

# Настройка логирования
logger = logging.getLogger(__name__)


def validate_data(data: Dict[str, Any]) -> bool:
    """
    Валидирует входные данные для ML задачи.
    
    Args:
        data: Входные данные для валидации
        
    Returns:
        bool: True, если данные валидны, иначе False
    """
    try:
        # Проверяем наличие необходимых полей
        if not isinstance(data, dict):
            logger.error("Данные не являются словарем")
            return False
        
        required_fields = ["prediction_id", "user_id", "data"]
        for field in required_fields:
            if field not in data:
                logger.error(f"Отсутствует обязательное поле: {field}")
                return False
        
        # Проверяем, что data содержит текст
        if not isinstance(data["data"], dict) or "text" not in data["data"]:
            logger.error("В данных отсутствует текст для анализа")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при валидации данных: {e}")
        return False


def make_prediction(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполняет предсказание на основе входных данных.
    
    Args:
        input_data: Входные данные для предсказания
        
    Returns:
        dict: Результат предсказания
    """
    # В реальном приложении здесь был бы код для загрузки модели и выполнения предсказания
    # Для демонстрации используем имитацию
    try:
        input_text = input_data.get("text", "").lower()
        
        # Добавляем задержку для имитации работы модели
        time.sleep(random.uniform(1.0, 3.0))
        
        # Список возможных результатов
        possible_results = [
            {"prediction": "Положительный результат", "confidence": round(random.uniform(0.7, 0.95), 2)},
            {"prediction": "Отрицательный результат", "confidence": round(random.uniform(0.6, 0.85), 2)},
            {"prediction": "Неопределенный результат", "confidence": round(random.uniform(0.4, 0.6), 2)}
        ]
        
        # Выбираем результат на основе текста
        if "хорошо" in input_text or "успех" in input_text or "положительно" in input_text:
            result = possible_results[0]
        elif "плохо" in input_text or "неудача" in input_text or "отрицательно" in input_text:
            result = possible_results[1]
        else:
            # Случайный выбор результата
            weights = [0.3, 0.3, 0.4]
            result = random.choices(possible_results, weights=weights, k=1)[0]
        
        # Добавляем дополнительную информацию
        result["timestamp"] = datetime.now().isoformat()
        result["worker_id"] = WORKER_ID
        result["input_text"] = input_text
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {e}")
        return {"error": str(e)} 