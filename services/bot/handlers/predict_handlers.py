"""
Обработчики команд предсказания эмоций по фотографии.
"""
import logging
import base64
import io
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from services import (
    create_prediction,
    get_prediction_status,
    get_user_predictions
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Определяем состояния для FSM
class PredictionStates(StatesGroup):
    """Состояния для машины состояний предсказания."""
    waiting_for_photo = State() # Ожидание загрузки фото


async def cmd_predict(message: types.Message):
    """
    Обрабатывает команду /predict.
    Запрашивает фотографию для анализа эмоций.
    """
    await message.reply(
        "Пожалуйста, отправьте фотографию лица человека для распознавания эмоций. "
        "Или отправьте /cancel для отмены.\n\n"
        "Для наилучших результатов рекомендуется фотография с четким изображением лица."
    )
    await PredictionStates.waiting_for_photo.set()


async def cancel_prediction(message: types.Message, state: FSMContext):
    """
    Отменяет текущее предсказание.
    """
    await state.finish()
    await message.reply("Предсказание отменено.")


async def process_photo(message: types.Message, state: FSMContext):
    """
    Обрабатывает фото, отправленное пользователем для предсказания эмоций.
    """
    if not message.photo:
        await message.reply("Пожалуйста, отправьте фотографию. Или используйте /cancel для отмены.")
        return
    
    telegram_id = message.from_user.id
    
    # Получаем информацию о фото (выбираем наибольший размер)
    photo = message.photo[-1]
    
    # Загружаем фото
    await message.reply("Получаю фотографию и подготавливаю анализ... ⏳")
    
    try:
        # Скачиваем файл
        photo_file = await photo.get_file()
        photo_bytes = await message.bot.download_file(photo_file.file_path)
        
        # Конвертируем в base64
        photo_base64 = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
        
        # Создаем предсказание
        prediction_id = await create_prediction(telegram_id, photo_base64)
        
        # Сохраняем ID предсказания в состоянии
        await state.update_data(prediction_id=prediction_id)
        
        # Сбрасываем состояние
        await state.finish()
        
        await message.reply(
            f"Фотография загружена! Начинаю анализ эмоций.\n\n"
            f"Предсказание #{prediction_id} создано.\n"
            f"Ваш запрос обрабатывается. Это может занять некоторое время.\n"
            f"Используйте команду /status {prediction_id} для проверки статуса."
        )
        
    except ValueError as e:
        await message.reply(f"Ошибка: {str(e)}")
        await state.finish()
        
    except Exception as e:
        logger.error(f"Ошибка при создании предсказания: {e}")
        await message.reply("Произошла ошибка при обработке фотографии. Пожалуйста, попробуйте позже.")
        await state.finish()


async def cmd_prediction_status(message: types.Message):
    """
    Обрабатывает команду /status.
    Проверяет статус предсказания по ID.
    """
    # Извлекаем ID предсказания из сообщения
    args = message.get_args().split()
    
    if not args:
        await message.reply(
            "Пожалуйста, укажите ID предсказания.\n"
            "Например: /status 123e4567-e89b-12d3-a456-426614174000"
        )
        return
    
    prediction_id = args[0]
    
    try:
        # Получаем информацию о предсказании
        prediction = await get_prediction_status(prediction_id)
        
        # Формируем ответ в зависимости от статуса
        if prediction["status"] == "pending":
            status_text = "⏳ В обработке"
        elif prediction["status"] == "completed":
            status_text = "✅ Завершено"
        elif prediction["status"] == "failed":
            status_text = "❌ Ошибка"
        else:
            status_text = f"Статус: {prediction['status']}"
        
        # Формируем сообщение с результатом
        message_text = f"Предсказание #{prediction['prediction_id']}\n\n"
        message_text += f"Статус: {status_text}\n"
        message_text += f"Создано: {prediction['created_at']}\n"
        
        if prediction["completed_at"]:
            message_text += f"Завершено: {prediction['completed_at']}\n"
        
        message_text += f"Стоимость: {prediction['cost']} кредитов\n\n"
        
        if prediction["result"]:
            # Проверяем наличие поля prediction в результате
            if "prediction" in prediction["result"]:
                message_text += f"Результат анализа эмоций:\n{prediction['result']['prediction']}\n\n"
                
                # Добавляем детали, если они есть
                if "confidence" in prediction["result"]:
                    message_text += f"Уверенность: {prediction['result']['confidence'] * 100:.1f}%\n"
                
                if "dominant_emotion" in prediction["result"]:
                    message_text += f"Определенная эмоция: {prediction['result']['translated_emotion']}\n"
            else:
                message_text += "Результат: Данные анализа недоступны\n"
        
        await message.reply(message_text)
        
    except ValueError as e:
        await message.reply(f"Ошибка: {str(e)}")
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса предсказания: {e}")
        await message.reply("Произошла ошибка при получении информации о предсказании.")


async def cmd_prediction_history(message: types.Message):
    """
    Обрабатывает команду /history.
    Показывает историю предсказаний пользователя.
    """
    telegram_id = message.from_user.id
    
    try:
        # Получаем историю предсказаний пользователя, передавая Telegram ID
        predictions = await get_user_predictions(telegram_id)
        
        if not predictions:
            await message.reply("У вас пока нет предсказаний эмоций. Используйте /predict, чтобы создать новое.")
            return
        
        # Формируем сообщение с историей
        message_text = "Ваши последние анализы эмоций:\n\n"
        
        for i, prediction in enumerate(predictions, 1):
            # Определяем статус
            if prediction["status"] == "pending":
                status_text = "⏳ В обработке"
            elif prediction["status"] == "completed":
                status_text = "✅ Завершено"
            elif prediction["status"] == "failed":
                status_text = "❌ Ошибка"
            else:
                status_text = f"Статус: {prediction['status']}"
            
            # Добавляем информацию о предсказании
            message_text += f"{i}. Предсказание #{prediction['prediction_id']}\n"
            message_text += f"   Статус: {status_text}\n"
            message_text += f"   Создано: {prediction['created_at']}\n"
            
            # Если предсказание завершено, добавляем результат
            if prediction["status"] == "completed" and prediction["result"] and "prediction" in prediction["result"]:
                result_preview = prediction["result"]["prediction"]
                if len(result_preview) > 50:
                    result_preview = result_preview[:50] + "..."
                message_text += f"   Результат: {result_preview}\n"
            
            message_text += f"   Стоимость: {prediction['cost']} кредитов\n\n"
        
        message_text += "Используйте команду /status <id> для получения подробной информации."
        
        await message.reply(message_text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории предсказаний: {e}")
        await message.reply("Произошла ошибка при получении истории предсказаний.") 