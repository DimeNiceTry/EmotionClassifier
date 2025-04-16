import logging
import os
import sys
import json
import time
import random
import pika
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
log_level = os.getenv("LOG_LEVEL", "INFO")
numeric_level = getattr(logging, log_level.upper(), logging.INFO)
logging.basicConfig(
    level=numeric_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Отладочные сообщения
logger.info("================= ЗАПУСК TELEGRAM БОТА =================")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables: LOG_LEVEL={log_level}")

# Настройки Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("Не задан токен Telegram бота. Установите переменную окружения TELEGRAM_TOKEN")
    sys.exit(1)
logger.info(f"Используется токен Telegram: {TELEGRAM_TOKEN[:8]}...{TELEGRAM_TOKEN[-5:]}")

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
ML_TASK_QUEUE = "ml_tasks"
ML_RESULT_QUEUE = "ml_results"

# Настройки PostgreSQL
DB_HOST = os.getenv("DB_HOST", "database")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ml_service")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Настройки ML
PREDICTION_COST = float(os.getenv("PREDICTION_COST", "1.0"))

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определение состояний
class PredictionStates(StatesGroup):
    waiting_for_text = State()

# Получение соединения с БД
def get_db_connection():
    """Создает соединение с базой данных"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise

def wait_for_db():
    """Ожидает доступности базы данных"""
    retry_count = 0
    max_retries = 30
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к PostgreSQL (попытка {retry_count + 1}/{max_retries})...")
            conn = get_db_connection()
            logger.info("Подключение к PostgreSQL успешно установлено")
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к PostgreSQL после нескольких попыток")
    return False

# Работа с RabbitMQ
def get_rabbitmq_connection():
    """Создает соединение с RabbitMQ"""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

def wait_for_rabbitmq():
    """Ожидает доступности RabbitMQ"""
    retry_count = 0
    max_retries = 30
    
    while retry_count < max_retries:
        try:
            logger.info(f"Пытаемся подключиться к RabbitMQ (попытка {retry_count + 1}/{max_retries})...")
            connection = get_rabbitmq_connection()
            logger.info("Подключение к RabbitMQ успешно установлено")
            connection.close()
            return True
        except Exception as e:
            logger.warning(f"RabbitMQ недоступен, ошибка: {e}")
            retry_count += 1
            time.sleep(5)
    
    logger.error("Не удалось подключиться к RabbitMQ после нескольких попыток")
    return False

def publish_message(message, queue_name=ML_TASK_QUEUE):
    """Публикует сообщение в очередь RabbitMQ"""
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Объявляем очередь
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Публикуем сообщение
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message).encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=2,  # сообщение будет сохранено на диск
                content_type='application/json'
            )
        )
        
        connection.close()
        logger.info(f"Сообщение отправлено в очередь {queue_name}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        return False

# Регистрация пользователя
async def register_user(telegram_id, username):
    """Регистрирует пользователя в системе"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{telegram_id}",))
        user = cursor.fetchone()
        
        if not user:
            # Создаем нового пользователя
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                (f"tg_{telegram_id}", f"{username}@telegram.org", f"tg_pass_{telegram_id}")
            )
            user_id = cursor.fetchone()["id"]
            
            # Создаем баланс для пользователя
            cursor.execute(
                "INSERT INTO balances (user_id, amount) VALUES (%s, %s)",
                (user_id, 10.0)  # Даем 10 кредитов новому пользователю
            )
            
            conn.commit()
            logger.info(f"Зарегистрирован новый пользователь: {username} (ID: {telegram_id})")
            return user_id
        else:
            logger.info(f"Пользователь уже существует: {username} (ID: {telegram_id})")
            return user["id"]
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return None
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

async def get_user_balance(user_id):
    """Получает баланс пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (user_id,))
        balance = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if balance:
            return balance["amount"]
        else:
            return 0.0
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {e}")
        return None

async def create_prediction(user_id, text):
    """Создает предсказание и отправляет задачу в очередь"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Проверяем баланс пользователя
        cursor.execute("SELECT amount FROM balances WHERE user_id = %s", (user_id,))
        balance = cursor.fetchone()
        
        if not balance or balance["amount"] < PREDICTION_COST:
            cursor.close()
            conn.close()
            return {"success": False, "message": "Недостаточно средств на балансе"}
        
        # Генерируем ID для предсказания
        prediction_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Записываем предсказание в БД
        cursor.execute(
            """
            INSERT INTO predictions (id, user_id, input_data, status, cost, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (prediction_id, user_id, json.dumps({"text": text}), "pending", PREDICTION_COST, timestamp)
        )
        
        # Списываем средства с баланса
        cursor.execute(
            """
            UPDATE balances
            SET amount = amount - %s, updated_at = %s
            WHERE user_id = %s
            """,
            (PREDICTION_COST, timestamp, user_id)
        )
        
        # Записываем транзакцию
        cursor.execute(
            """
            INSERT INTO transactions (user_id, amount, type, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, -PREDICTION_COST, "prediction", "completed", timestamp)
        )
        
        conn.commit()
        
        # Формируем сообщение для очереди
        message = {
            "prediction_id": prediction_id,
            "user_id": user_id,
            "data": {"text": text},
            "timestamp": timestamp.isoformat(),
            "source": "telegram_bot"
        }
        
        # Отправляем сообщение в очередь
        if not publish_message(message):
            # Обработка ошибки отправки
            logger.error(f"Не удалось отправить задание в очередь для предсказания {prediction_id}")
            
            # Восстанавливаем баланс и помечаем предсказание как failed
            cursor.execute(
                """
                UPDATE predictions
                SET status = %s
                WHERE id = %s
                """,
                ("failed", prediction_id)
            )
            
            cursor.execute(
                """
                UPDATE balances
                SET amount = amount + %s, updated_at = %s
                WHERE user_id = %s
                """,
                (PREDICTION_COST, datetime.now(), user_id)
            )
            
            cursor.execute(
                """
                INSERT INTO transactions (user_id, amount, type, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, PREDICTION_COST, "refund", "completed", datetime.now())
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {"success": False, "message": "Сервис ML временно недоступен"}
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "prediction_id": prediction_id,
            "status": "pending",
            "timestamp": timestamp,
            "cost": PREDICTION_COST
        }
    except Exception as e:
        logger.error(f"Ошибка при создании предсказания: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
        return {"success": False, "message": "Внутренняя ошибка сервера"}

async def get_prediction_status(prediction_id):
    """Получает статус предсказания"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM predictions WHERE id = %s", (prediction_id,))
        prediction = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not prediction:
            return {"success": False, "message": "Предсказание не найдено"}
        
        return {
            "success": True,
            "status": prediction["status"],
            "result": json.loads(prediction["result"]) if prediction["result"] else None,
            "created_at": prediction["created_at"]
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статуса предсказания: {e}")
        return {"success": False, "message": f"Ошибка: {str(e)}"}

# Обработчики команд бота
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Обработчик команд /start и /help"""
    logger.info(f"Получена команда /start или /help от пользователя {message.from_user.id}")
    try:
        # Регистрируем пользователя
        user_id = await register_user(message.from_user.id, message.from_user.username or "anonymous")
        
        # Отправляем приветственное сообщение
        welcome_text = (
            "👋 Привет! Я бот для определения эмоций в тексте.\n\n"
            "🔹 Отправьте мне текст, и я определю его эмоциональную окраску\n"
            "🔹 Используйте /balance для проверки баланса\n"
            "🔹 Используйте /history для просмотра истории предсказаний\n"
            "🔹 Каждое предсказание стоит 1 кредит\n\n"
            "Начните прямо сейчас - отправьте мне текст для анализа!"
        )
        await message.reply(welcome_text)
        logger.info(f"Отправлено приветственное сообщение пользователю {message.from_user.id}")
    except Exception as e:
        error_message = "Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже."
        logger.error(f"Ошибка при обработке /start: {e}")
        await message.reply(error_message)

@dp.message_handler(lambda message: message.text and not message.text.startswith('/'))
async def handle_text(message: types.Message):
    """Обработчик текстовых сообщений"""
    logger.info(f"Получено текстовое сообщение от пользователя {message.from_user.id}: {message.text[:50]}...")
    
    try:
        # Получаем ID пользователя из базы данных
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{message.from_user.id}",))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            await message.reply("Вы не зарегистрированы. Используйте /start для регистрации.")
            return
        
        # Создаем предсказание
        await message.reply("⏳ Отправляем запрос на анализ эмоциональной окраски текста...")
        result = await create_prediction(user["id"], message.text)
        
        if result["success"]:
            prediction_id = result["prediction_id"]
            
            # Создаем клавиатуру для проверки статуса
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Проверить статус", callback_data=f"check_status:{prediction_id}"))
            
            await message.reply(
                "✅ Запрос успешно отправлен!\n\n"
                "Анализ текста выполняется и будет готов через некоторое время.\n"
                "Вы можете проверить статус с помощью кнопки ниже.",
                reply_markup=keyboard
            )
        else:
            await message.reply(f"❌ Ошибка: {result['message']}")
    except Exception as e:
        error_message = "Произошла ошибка при обработке текста. Пожалуйста, попробуйте позже."
        logger.error(f"Ошибка при обработке текста: {e}")
        await message.reply(error_message)

@dp.message_handler(commands=['balance'])
async def get_balance_command(message: types.Message):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{message.from_user.id}",))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        await message.reply("Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    balance = await get_user_balance(user["id"])
    
    if balance is not None:
        await message.reply(f"Ваш текущий баланс: {balance:.2f} кредитов.")
    else:
        await message.reply("Не удалось получить информацию о балансе. Пожалуйста, попробуйте позже.")

@dp.message_handler(commands=['predict'])
async def predict_command(message: types.Message):
    await PredictionStates.waiting_for_text.set()
    await message.reply(
        "Пожалуйста, отправьте текст для анализа. "
        f"Стоимость одного предсказания: {PREDICTION_COST} кредитов."
    )

@dp.message_handler(state=PredictionStates.waiting_for_text)
async def process_prediction(message: types.Message, state: FSMContext):
    text = message.text
    
    # Получаем ID пользователя
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{message.from_user.id}",))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not user:
        await message.reply("Вы не зарегистрированы. Используйте /start для регистрации.")
        await state.finish()
        return
    
    # Создаем предсказание
    await message.reply("⏳ Отправляем запрос на предсказание...")
    result = await create_prediction(user["id"], text)
    
    if result["success"]:
        prediction_id = result["prediction_id"]
        
        # Создаем клавиатуру для проверки статуса
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Проверить статус", callback_data=f"check_status:{prediction_id}"))
        
        await message.reply(
            "✅ Запрос успешно отправлен!\n\n"
            "Предсказание обрабатывается и будет готово через некоторое время.\n"
            "Вы можете проверить статус с помощью кнопки ниже.",
            reply_markup=keyboard
        )
    else:
        await message.reply(f"❌ Ошибка: {result['message']}")
    
    await state.finish()

@dp.callback_query_handler(lambda call: call.data.startswith('check_status:'))
async def check_status_callback(call: types.CallbackQuery):
    prediction_id = call.data.split(':')[1]
    
    await call.answer("Проверяем статус предсказания...")
    
    # Получаем статус предсказания
    status_result = await get_prediction_status(prediction_id)
    
    if status_result["success"]:
        status = status_result["status"]
        
        if status == "completed" and status_result["result"]:
            result = status_result["result"]
            prediction_text = result.get("prediction", "Нет результата")
            confidence = result.get("confidence", 0)
            
            message_text = (
                "✅ Предсказание готово!\n\n"
                f"Результат: {prediction_text}\n"
                f"Уверенность: {confidence:.2f}"
            )
            
            # Обновляем сообщение без клавиатуры
            await bot.edit_message_text(
                message_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
        elif status == "pending":
            # Обновляем сообщение с той же клавиатурой
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Проверить статус", callback_data=f"check_status:{prediction_id}"))
            
            await bot.edit_message_text(
                "⏳ Предсказание все еще обрабатывается. Пожалуйста, проверьте позже.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard
            )
        else:
            await bot.edit_message_text(
                f"ℹ️ Статус предсказания: {status}",
                call.message.chat.id,
                call.message.message_id
            )
    else:
        await bot.edit_message_text(
            f"❌ Ошибка: {status_result['message']}",
            call.message.chat.id,
            call.message.message_id
        )

@dp.message_handler(commands=['history'])
async def history_command(message: types.Message):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получаем ID пользователя
    cursor.execute("SELECT id FROM users WHERE username = %s", (f"tg_{message.from_user.id}",))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        await message.reply("Вы не зарегистрированы. Используйте /start для регистрации.")
        return
    
    # Получаем последние 5 предсказаний
    cursor.execute(
        """
        SELECT id, status, result, created_at, cost 
        FROM predictions 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 5
        """,
        (user["id"],)
    )
    predictions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not predictions:
        await message.reply("У вас еще нет истории предсказаний.")
        return
    
    history_text = "📜 Ваша история предсказаний:\n\n"
    
    for i, prediction in enumerate(predictions, 1):
        status = prediction["status"]
        result = json.loads(prediction["result"]) if prediction["result"] else None
        created_at = prediction["created_at"].strftime("%d.%m.%Y %H:%M:%S")
        
        history_text += f"{i}. Дата: {created_at}\n"
        history_text += f"   Статус: {status}\n"
        
        if result and status == "completed":
            prediction_text = result.get("prediction", "Нет результата")
            confidence = result.get("confidence", 0)
            history_text += f"   Результат: {prediction_text}\n"
            history_text += f"   Уверенность: {confidence:.2f}\n"
        
        history_text += f"   Стоимость: {prediction['cost']:.2f} кредитов\n\n"
    
    await message.reply(history_text)

# Обработка результатов из RabbitMQ
async def consume_results():
    """Запускает потребителя для обработки результатов из очереди"""
    while True:
        try:
            # Ожидаем доступности RabbitMQ
            if not wait_for_rabbitmq():
                logger.error("Не удалось подключиться к RabbitMQ для получения результатов. Повторная попытка через 10 секунд.")
                await asyncio.sleep(10)
                continue
                
            # Подключаемся к RabbitMQ
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            
            # Объявляем очередь
            channel.queue_declare(queue=ML_RESULT_QUEUE, durable=True)
            
            # Определяем обработчик сообщений
            def callback(ch, method, properties, body):
                asyncio.create_task(process_result(body))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
            # Настраиваем получение сообщений
            channel.basic_consume(
                queue=ML_RESULT_QUEUE,
                on_message_callback=callback
            )
            
            logger.info("Бот готов получать результаты из очереди")
            
            # Начинаем получать сообщения
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Потеряно соединение с RabbitMQ: {e}. Переподключение через 5 секунд...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Ошибка при получении результатов: {e}")
            await asyncio.sleep(5)

async def process_result(body):
    """Обрабатывает результат предсказания"""
    try:
        message = json.loads(body.decode('utf-8'))
        logger.info(f"Получен результат предсказания: {message.get('prediction_id', 'unknown')}")
        
        prediction_id = message.get("prediction_id")
        user_id = message.get("user_id")
        result = message.get("result")
        
        if not prediction_id or not user_id or not result:
            logger.error("Некорректные данные в результате предсказания")
            return
        
        # Получаем информацию о предсказании из БД
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM predictions WHERE id = %s AND user_id = %s",
            (prediction_id, user_id)
        )
        prediction = cursor.fetchone()
        
        if not prediction:
            logger.error(f"Предсказание {prediction_id} не найдено в БД")
            cursor.close()
            conn.close()
            return
        
        # Получаем информацию о пользователе в Telegram
        cursor.execute(
            "SELECT username FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not user:
            logger.error(f"Пользователь {user_id} не найден в БД")
            return
        
        # Извлекаем id пользователя из имени пользователя (формат: tg_USERID)
        username = user.get("username", "")
        if not username.startswith("tg_"):
            logger.error(f"Некорректный формат имени пользователя: {username}")
            return
        
        telegram_id = username[3:]  # Удаляем префикс tg_
        
        try:
            telegram_id = int(telegram_id)
        except ValueError:
            logger.error(f"Некорректный ID пользователя Telegram: {telegram_id}")
            return
        
        # Формируем сообщение с результатом
        prediction_text = prediction.get("input_data", {}).get("text", "текст не указан")
        prediction_result = result.get("prediction", "результат недоступен")
        confidence = result.get("confidence", 0.0)
        worker_id = result.get("processed_by", "неизвестно")
        
        message_text = (
            f"✅ <b>Результат вашего предсказания готов!</b>\n\n"
            f"<b>ID:</b> <code>{prediction_id}</code>\n"
            f"<b>Запрос:</b> {prediction_text}\n"
            f"<b>Результат:</b> {prediction_result}\n"
            f"<b>Уверенность:</b> {confidence * 100:.1f}%\n"
            f"<b>Обработано:</b> {worker_id}\n"
        )
        
        # Отправляем сообщение пользователю
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Результат предсказания {prediction_id} отправлен пользователю {telegram_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {telegram_id}: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке результата: {e}")

# Запуск бота
async def on_startup(dp):
    """Действия при запуске бота"""
    logger.info("Запуск бота...")
    
    # Проверяем подключение к Telegram API
    try:
        bot_info = await dp.bot.get_me()
        logger.info(f"Подключение к Telegram API успешно. Бот: {bot_info.full_name} (@{bot_info.username})")
    except Exception as e:
        logger.error(f"Ошибка при подключении к Telegram API: {e}")
        raise
    
    # Проверяем подключение к базе данных
    if not wait_for_db():
        logger.error("Не удалось подключиться к базе данных")
        raise Exception("Database connection failed")
    logger.info("Подключение к базе данных успешно")
    
    # Проверяем подключение к RabbitMQ
    if not wait_for_rabbitmq():
        logger.error("Не удалось подключиться к RabbitMQ")
        raise Exception("RabbitMQ connection failed")
    logger.info("Подключение к RabbitMQ успешно")
    
    # Запускаем прослушивание очереди результатов
    asyncio.create_task(consume_results())
    logger.info("Запущено прослушивание очереди результатов")
    
    # Проверяем webhook
    try:
        webhook_info = await dp.bot.get_webhook_info()
        logger.info(f"Webhook info: {webhook_info}")
        if webhook_info.url:
            logger.warning(f"Webhook установлен на {webhook_info.url}. Это может мешать работе бота.")
            # Удаляем webhook
            await dp.bot.delete_webhook()
            logger.info("Webhook удален")
    except Exception as e:
        logger.error(f"Ошибка при проверке webhook: {e}")
    
    logger.info("Бот успешно запущен и готов к работе")

if __name__ == '__main__':
    try:
        # Запускаем бота
        executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1) 