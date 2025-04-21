"""
Обработчики команд для работы с балансом.
"""
import logging
import re
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from services import get_user_balance, add_user_balance
from services.db_service import get_db_connection, get_db_user_id

# Настройка логирования
logger = logging.getLogger(__name__)

# Состояния для пополнения баланса
class BalanceStates(StatesGroup):
    waiting_for_amount = State()

async def cmd_balance(message: types.Message):
    """
    Обрабатывает команду /balance.
    Показывает текущий баланс пользователя.
    """
    telegram_id = message.from_user.id
    
    try:
        # Получаем внутренний ID пользователя из базы данных
        db_user_id = await get_db_user_id(telegram_id)
        
        if not db_user_id:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            await message.reply("Ошибка: ваш аккаунт не найден. Пожалуйста, используйте /start для регистрации.")
            return
        
        # Получаем баланс пользователя используя внутренний ID
        balance = await get_user_balance(db_user_id)
        
        # Отправляем сообщение с балансом
        await message.reply(
            f"Ваш текущий баланс: {balance:.2f} кредитов\n\n"
            "Каждое предсказание стоит 1 кредит.\n"
            "Новые пользователи получают 10 кредитов при регистрации.\n\n"
            "Для пополнения баланса используйте команду /topup"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        await message.reply("Произошла ошибка при получении информации о балансе.")

async def cmd_topup(message: types.Message):
    """
    Обрабатывает команду /topup.
    Запускает процесс пополнения баланса.
    """
    await message.reply(
        "Введите сумму пополнения (число от 1 до 100):"
    )
    # Устанавливаем состояние ожидания суммы пополнения
    await BalanceStates.waiting_for_amount.set()

async def process_topup_amount(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод суммы пополнения.
    """
    telegram_id = message.from_user.id
    text = message.text.strip()
    
    # Проверяем, что введено число
    if not re.match(r'^\d+(\.\d+)?$', text):
        await message.reply("Пожалуйста, введите корректное число.")
        return
    
    amount = float(text)
    
    # Проверяем, что сумма в допустимых пределах
    if amount < 1 or amount > 100:
        await message.reply("Сумма пополнения должна быть от 1 до 100 кредитов.")
        return
    
    try:
        # Получаем внутренний ID пользователя из базы данных
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info(f"Получение внутреннего ID пользователя для Telegram ID: {telegram_id}")
        cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{telegram_id}",))
        user_record = cursor.fetchone()
        
        if not user_record:
            logger.error(f"Пользователь с Telegram ID {telegram_id} не найден в базе данных")
            await message.reply("Ошибка: ваш аккаунт не найден. Пожалуйста, используйте /start для регистрации.")
            await state.finish()
            conn.close()
            return
        
        db_user_id = user_record[0]
        logger.info(f"Найден внутренний ID пользователя: {db_user_id} для Telegram ID: {telegram_id}")
        conn.close()
        
        # Пополняем баланс используя внутренний ID
        new_balance = await add_user_balance(db_user_id, amount)
        
        # Сбрасываем состояние
        await state.finish()
        
        # Отправляем сообщение об успешном пополнении
        await message.reply(
            f"Баланс успешно пополнен на {amount:.2f} кредитов.\n"
            f"Ваш новый баланс: {new_balance:.2f} кредитов."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при пополнении баланса: {e}")
        await message.reply("Произошла ошибка при пополнении баланса.")
        await state.finish()

async def cancel_topup(message: types.Message, state: FSMContext):
    """
    Отменяет процесс пополнения баланса.
    """
    current_state = await state.get_state()
    if current_state == BalanceStates.waiting_for_amount.state:
        await state.finish()
        await message.reply("Пополнение баланса отменено.")
        return True
    return False 