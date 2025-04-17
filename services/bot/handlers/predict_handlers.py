"""
Обработчики команд предсказания.
"""
import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from services.bot.services import (
    create_prediction,
    get_prediction_status,
    get_user_predictions
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Определяем состояния для FSM
class PredictionStates(StatesGroup):
    """Состояния для машины состояний предсказания."""
    waiting_for_text = State() # Ожидание ввода текста


async def cmd_predict(message: types.Message):
    """
    Обрабатывает команду /predict.
    Запрашивает текст для предсказания.
    """
    await message.reply(
        "Пожалуйста, введите текст для анализа и предсказания. "
        "Или отправьте /cancel для отмены."
    )
    await PredictionStates.waiting_for_text.set()


async def cancel_prediction(message: types.Message, state: FSMContext):
    """
    Отменяет текущее предсказание.
    """
    await state.finish()
    await message.reply("Предсказание отменено.")


async def process_prediction_text(message: types.Message, state: FSMContext):
    """
    Обрабатывает текст, введенный пользователем для предсказания.
    """
    user_id = message.from_user.id
    text = message.text
    
    await message.reply("Обрабатываю ваш запрос... ⏳")
    
    try:
        # Создаем предсказание
        prediction_id = await create_prediction(user_id, text)
        
        # Сохраняем ID предсказания в состоянии
        await state.update_data(prediction_id=prediction_id)
        
        # Сбрасываем состояние
        await state.finish()
        
        await message.reply(
            f"Предсказание #{prediction_id} создано!\n\n"
            "Ваш запрос обрабатывается. Это может занять некоторое время.\n"
            "Используйте команду /status {prediction_id} для проверки статуса."
        )
        
    except ValueError as e:
        await message.reply(f"Ошибка: {str(e)}")
        await state.finish()
        
    except Exception as e:
        logger.error(f"Ошибка при создании предсказания: {e}")
        await message.reply("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
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
            message_text += "Результат:\n"
            message_text += f"{prediction['result']['prediction']}"
        
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
    user_id = message.from_user.id
    
    try:
        # Получаем историю предсказаний пользователя
        predictions = await get_user_predictions(user_id)
        
        if not predictions:
            await message.reply("У вас пока нет предсказаний.")
            return
        
        # Формируем сообщение с историей
        message_text = "Ваши последние предсказания:\n\n"
        
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
            message_text += f"   Стоимость: {prediction['cost']} кредитов\n\n"
        
        message_text += "Используйте команду /status <id> для получения подробной информации."
        
        await message.reply(message_text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории предсказаний: {e}")
        await message.reply("Произошла ошибка при получении истории предсказаний.") 