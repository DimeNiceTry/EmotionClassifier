"""
Обработчики команд для работы с балансом.
"""
import logging
from aiogram import types
from services.bot.services import get_user_balance

# Настройка логирования
logger = logging.getLogger(__name__)

async def cmd_balance(message: types.Message):
    """
    Обрабатывает команду /balance.
    Показывает текущий баланс пользователя.
    """
    user_id = message.from_user.id
    
    try:
        # Получаем баланс пользователя
        balance = await get_user_balance(user_id)
        
        # Отправляем сообщение с балансом
        await message.reply(
            f"Ваш текущий баланс: {balance:.2f} кредитов\n\n"
            "Каждое предсказание стоит 1 кредит.\n"
            "Новые пользователи получают 10 кредитов при регистрации."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        await message.reply("Произошла ошибка при получении информации о балансе.") 