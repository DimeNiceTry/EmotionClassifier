"""
Сервис для работы с моделями машинного обучения.
"""
import logging
import time
import os
import base64
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, Union, List
import uuid

import numpy as np
from PIL import Image
import io
from deepface import DeepFace

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
        
        # Проверяем, что data содержит изображение
        if not isinstance(data["data"], dict) or "image" not in data["data"]:
            logger.error("В данных отсутствует изображение для анализа")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при валидации данных: {e}")
        return False


def decode_image(image_data: str) -> Union[np.ndarray, None]:
    """
    Декодирует изображение из base64 строки
    
    Args:
        image_data: Изображение в формате base64
        
    Returns:
        np.ndarray: Массив с изображением или None в случае ошибки
    """
    try:
        # Декодируем base64 в бинарные данные
        if "base64," in image_data:
            # Убираем метаданные если они есть (например, "data:image/jpeg;base64,")
            image_data = image_data.split("base64,")[1]
            
        image_bytes = base64.b64decode(image_data)
        
        # Создаем временный файл для сохранения изображения
        # DeepFace работает лучше с файлами, чем с массивами
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        temp_file.write(image_bytes)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        logger.error(f"Ошибка при декодировании изображения: {e}")
        return None


def analyze_emotion(image_path: str) -> Dict[str, Any]:
    """
    Анализирует эмоции на фотографии с помощью DeepFace
    
    Args:
        image_path: Путь к изображению
        
    Returns:
        dict: Результат анализа эмоций
    """
    try:
        # Анализируем эмоции с помощью DeepFace
        logger.info(f"Анализ эмоций для изображения {image_path}")
        result = DeepFace.analyze(
            img_path=image_path,
            actions=['emotion'],
            enforce_detection=False,  # Не прерывать выполнение, если лицо не обнаружено
            detector_backend='opencv'
        )
        
        # Удаляем временный файл
        os.unlink(image_path)
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при анализе эмоций: {e}")
        # Пытаемся удалить временный файл даже в случае ошибки
        try:
            if os.path.exists(image_path):
                os.unlink(image_path)
        except:
            pass
        return {"error": str(e)}


def format_emotion_result(raw_result: Union[List, Dict]) -> Dict[str, Any]:
    """
    Форматирует результат анализа эмоций
    
    Args:
        raw_result: Сырой результат от DeepFace
        
    Returns:
        dict: Отформатированный результат
    """
    try:
        # DeepFace может вернуть список результатов, если на фото несколько лиц
        # Или словарь, если лицо одно
        if isinstance(raw_result, list):
            if not raw_result:  # Пустой список
                return {
                    "prediction": "Лица не обнаружены",
                    "faces_count": 0,
                    "dominant_emotion": None,
                    "emotions": {},
                    "confidence": 0
                }
            
            # Обрабатываем все лица
            faces = []
            for face in raw_result:
                if "emotion" in face:
                    emotion_data = face["emotion"]
                    dominant_emotion = max(emotion_data, key=emotion_data.get)
                    confidence = emotion_data[dominant_emotion]
                    
                    faces.append({
                        "dominant_emotion": dominant_emotion,
                        "emotions": emotion_data,
                        "confidence": confidence
                    })
            
            # Определяем доминирующую эмоцию для всех лиц
            if faces:
                # Выбираем лицо с наивысшей уверенностью
                best_face = max(faces, key=lambda x: x["confidence"])
                
                return {
                    "prediction": f"Обнаружено {len(faces)} лиц. Преобладающая эмоция: {translate_emotion(best_face['dominant_emotion'])}",
                    "faces_count": len(faces),
                    "faces": faces,
                    "dominant_emotion": best_face["dominant_emotion"],
                    "translated_emotion": translate_emotion(best_face["dominant_emotion"]),
                    "confidence": round(best_face["confidence"], 2)
                }
            else:
                return {
                    "prediction": "Эмоции не распознаны",
                    "faces_count": len(raw_result),
                    "dominant_emotion": None,
                    "emotions": {},
                    "confidence": 0
                }
        elif isinstance(raw_result, dict) and "emotion" in raw_result:
            # Один результат в словаре
            emotion_data = raw_result["emotion"]
            dominant_emotion = max(emotion_data, key=emotion_data.get)
            confidence = emotion_data[dominant_emotion]
            
            return {
                "prediction": f"Преобладающая эмоция: {translate_emotion(dominant_emotion)}",
                "faces_count": 1,
                "dominant_emotion": dominant_emotion,
                "translated_emotion": translate_emotion(dominant_emotion),
                "emotions": emotion_data,
                "confidence": round(confidence, 2)
            }
        else:
            return {
                "prediction": "Не удалось распознать эмоции",
                "faces_count": 0,
                "dominant_emotion": None,
                "emotions": {},
                "confidence": 0
            }
    except Exception as e:
        logger.error(f"Ошибка при форматировании результата: {e}")
        return {
            "prediction": f"Ошибка обработки: {str(e)}",
            "faces_count": 0,
            "dominant_emotion": None,
            "emotions": {},
            "confidence": 0
        }


def translate_emotion(emotion: str) -> str:
    """
    Переводит название эмоции на русский язык
    
    Args:
        emotion: Название эмоции на английском
        
    Returns:
        str: Название эмоции на русском
    """
    emotion_map = {
        "angry": "Злость",
        "disgust": "Отвращение",
        "fear": "Страх",
        "happy": "Счастье",
        "sad": "Грусть",
        "surprise": "Удивление",
        "neutral": "Нейтральное выражение",
        None: "Не определено"
    }
    return emotion_map.get(emotion, emotion)


def make_prediction(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполняет предсказание эмоций на фотографии.
    
    Args:
        input_data: Входные данные для предсказания
        
    Returns:
        dict: Результат предсказания
    """
    try:
        start_time = time.time()
        
        # Получаем изображение из входных данных
        image_data = input_data.get("image", "")
        
        # Декодируем изображение
        image_path = decode_image(image_data)
        if not image_path:
            return {
                "prediction": "Ошибка при обработке изображения",
                "error": "Failed to decode image",
                "timestamp": datetime.now().isoformat(),
                "worker_id": WORKER_ID
            }
        
        # Анализируем эмоции
        raw_result = analyze_emotion(image_path)
        
        # Если произошла ошибка при анализе
        if "error" in raw_result:
            return {
                "prediction": f"Ошибка при анализе эмоций: {raw_result['error']}",
                "error": raw_result["error"],
                "timestamp": datetime.now().isoformat(),
                "worker_id": WORKER_ID
            }
        
        # Форматируем результат
        result = format_emotion_result(raw_result)
        
        # Добавляем метаданные
        result["timestamp"] = datetime.now().isoformat()
        result["worker_id"] = WORKER_ID
        result["processing_time"] = round(time.time() - start_time, 2)
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {e}")
        return {
            "prediction": f"Произошла ошибка: {str(e)}",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "worker_id": WORKER_ID
        } 