"""
Общие обработчики команд Telegram бота.
"""
import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from services.bot.services.db_service import register_user

# Настройка логирования
logger = logging.getLogger(__name__)

async def send_welcome(message: types.Message):
    """
    Обрабатывает команды /start и /help.
    """
    # Регистрируем пользователя при первом использовании бота
    user_id = await register_user(message.from_user.id, message.from_user.username or "user")
    
    await message.reply(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я бот для демонстрации ML сервиса. С моей помощью ты можешь отправлять запросы "
        "на предсказание и получать результаты.\n\n"
        "Доступные команды:\n"
        "/predict - сделать предсказание\n"
        "/balance - проверить баланс\n"
        "/history - история предсказаний\n"
        "/help - показать это сообщение\n\n"
        "Для начала работы используй команду /predict и отправь мне текст для анализа."
    )

async def handle_text(message: types.Message):
    """
    Обрабатывает обычные текстовые сообщения.
    """
    await message.reply(
        "Я получил твое сообщение, но не знаю, что с ним делать.\n"
        "Используй команду /predict для создания нового предсказания."
    )