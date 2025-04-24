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
        
        # Проверяем, что нет текстового ввода (отключение текстового предсказания)
        if isinstance(data["data"], dict) and "text" in data["data"]:
            logger.error("Текстовые предсказания отключены")
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
        
        # Устанавливаем enforce_detection=False, чтобы DeepFace не требовал
        # строгого обнаружения лица и использовал более мягкие критерии
        result = DeepFace.analyze(
            img_path=image_path,
            actions=['emotion'],
            enforce_detection=True,  # Изменяем на False для увеличения чувствительности
            detector_backend='opencv'
        )
        
        # Удаляем временный файл
        os.unlink(image_path)
        
        # Проверяем, что результат не пустой
        if isinstance(result, list) and not result:
            return {
                "prediction": "Лица не обнаружены",
                "faces_count": 0,
                "dominant_emotion": None,
                "emotions": {},
                "confidence": 0,
                "error": "Face detection failed"
            }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при анализе эмоций: {e}")
        # Пытаемся удалить временный файл даже в случае ошибки
        try:
            if os.path.exists(image_path):
                os.unlink(image_path)
        except:
            pass
        
        # Если ошибка связана с не обнаружением лица, возвращаем специальный ответ
        error_message = str(e)
        if "Face could not be detected" in error_message or "No face detected" in error_message:
            return {
                "prediction": "Лица не обнаружены",
                "faces_count": 0,
                "dominant_emotion": None,
                "emotions": {},
                "confidence": 0,
                "error": "Face detection failed"
            }
            
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
        # Проверяем, содержит ли результат ошибку
        if isinstance(raw_result, dict) and "error" in raw_result:
            return {
                "prediction": "Лица не обнаружены",
                "faces_count": 0,
                "dominant_emotion": None,
                "emotions": {},
                "confidence": 0,
                "error": raw_result["error"]
            }

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
                    "prediction": "Лица не обнаружены",
                    "faces_count": 0,
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
                "prediction": "Лица не обнаружены",
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
        
        # Дополнительная проверка на отсутствие текстового предсказания
        if "text" in input_data:
            logger.error("Текстовые предсказания отключены")
            return {
                "prediction": "Текстовые предсказания отключены",
                "error": "Text predictions are disabled",
                "timestamp": datetime.now().isoformat(),
                "worker_id": WORKER_ID
            }
        
        # Получаем изображение из входных данных
        image_data = input_data.get("image", "")
        
        # Декодируем изображение
        image_path = decode_image(image_data)
        if not image_path:
            return {
                "prediction": "Ошибка при обработке изображения",
                "error": "Failed to decode image",
                "timestamp": datetime.now().isoformat(),
                "worker_id": WORKER_ID,
                "refund_credits": True,  # Добавляем флаг для возврата кредитов
                "status": "failed"  # Устанавливаем статус failed
            }
        
        # Анализируем эмоции
        raw_result = analyze_emotion(image_path)
        
        # Если произошла ошибка при анализе
        if isinstance(raw_result, dict) and "error" in raw_result:
            # Если ошибка связана с отсутствием лица
            if raw_result["error"] == "Face detection failed":
                prediction_result = {
                    "prediction": "Лица не обнаружены",
                    "faces_count": 0,
                    "dominant_emotion": None,
                    "emotions": {},
                    "confidence": 0,
                    "worker_id": WORKER_ID,
                    "timestamp": datetime.now().isoformat(),
                    "processing_time": round(time.time() - start_time, 1),
                    "refund_credits": True,  # Добавляем флаг для возврата кредитов
                    "status": "failed"  # Устанавливаем статус failed
                }
                logger.info(f"Лица не обнаружены, возвращаем кредиты: {prediction_result}")
                return prediction_result
            else:
                # Другие ошибки при анализе
                return {
                    "prediction": f"Ошибка при анализе эмоций: {raw_result['error']}",
                    "error": raw_result["error"],
                    "timestamp": datetime.now().isoformat(),
                    "worker_id": WORKER_ID,
                    "processing_time": round(time.time() - start_time, 1),
                    "refund_credits": True,  # Добавляем флаг для возврата кредитов
                    "status": "failed"  # Устанавливаем статус failed
                }
        
        # Форматируем результат
        formatted_result = format_emotion_result(raw_result)
        
        # Проверяем критерии возврата кредитов
        should_refund = False
        
        # Критерий 3: Количество обнаруженных лиц равно 0
        if formatted_result.get("faces_count", 0) == 0 or "Лица не обнаружены" in formatted_result.get("prediction", ""):
            should_refund = True
            formatted_result["status"] = "failed"
            logger.info(f"Лица не обнаружены, устанавливаем статус 'failed' и флаг возврата кредитов")
            
        # Критерий 4: Отсутствие информации об эмоциях
        elif not formatted_result.get("emotions") and not formatted_result.get("dominant_emotion"):
            should_refund = True
            formatted_result["status"] = "completed"  # Сохраняем статус completed для отслеживания этого случая
            logger.info(f"Отсутствует информация об эмоциях, устанавливаем флаг возврата кредитов")
            
        # Устанавливаем флаг возврата кредитов при необходимости
        if should_refund:
            formatted_result["refund_credits"] = True
        
        # Добавляем дополнительную информацию
        result = {
            **formatted_result,
            "timestamp": datetime.now().isoformat(),
            "worker_id": WORKER_ID,
            "processing_time": round(time.time() - start_time, 1)
        }
        
        logger.info(f"Предсказание выполнено успешно: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {e}")
        return {
            "prediction": f"Ошибка при выполнении предсказания: {str(e)}",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "worker_id": WORKER_ID,
            "refund_credits": True,  # Возвращаем кредиты при ошибке
            "status": "failed"  # Устанавливаем статус failed
        } 