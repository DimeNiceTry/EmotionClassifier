from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.request import HTTPXRequest
import httpx
import os
from dotenv import load_dotenv
import logging
from sqlalchemy.sql import func
from models import Session, User, Prediction, Notification, SystemStats, UserRole
from datetime import datetime, timedelta
import random
import json
from pathlib import Path
import sys
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
env_path = Path(__file__).parent.parent.parent / '.env'
logger.info(f"Путь к .env файлу: {env_path}")
load_dotenv(env_path)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Проверка токена
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

logger.info(f"Токен бота загружен: {TELEGRAM_BOT_TOKEN[:5]}...")

# Состояния для ConversationHandler
REGISTER, LOGIN, DEPOSIT, PREDICT, ADMIN_MENU = range(5)

# Стоимость предсказания
PREDICTION_COST = 10.0

# HTTP клиент для API
async def get_http_client():
    """Создает и возвращает HTTP клиент для запросов к API"""
    return httpx.AsyncClient(
        timeout=30.0,
        base_url=API_BASE_URL
    )

async def api_predict(input_data: dict) -> dict:
    """Выполняет запрос к API предсказаний"""
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
            # Отправляем задачу
            response = await client.post("/predictions/predict", json={"data": input_data})
            if response.status_code != 200:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return {"error": f"Ошибка API: {response.status_code}"}
            
            # Получаем данные о задаче
            prediction_data = response.json()
            prediction_id = prediction_data.get("prediction_id")
            
            if not prediction_id:
                return {"error": "Не удалось получить ID предсказания"}
                
            # Проверяем статус до 10 раз
            for _ in range(10):
                # Ждем немного перед проверкой
                await asyncio.sleep(1)
                
                # Проверяем статус задачи
                status_response = await client.get(f"/predictions/status/{prediction_id}")
                if status_response.status_code != 200:
                    continue
                    
                status_data = status_response.json()
                # Если задача завершена, возвращаем результат
                if status_data.get("status") == "completed":
                    return status_data
            
            # Если после 10 попыток нет результата, возвращаем что доступно
            return prediction_data
    except Exception as e:
        logger.error(f"Ошибка при обращении к API: {e}")
        return {"error": f"Ошибка соединения: {str(e)}"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if user:
        user.last_activity = datetime.utcnow()
        session.commit()
        
        keyboard = [
            [InlineKeyboardButton("💰 Баланс", callback_data='balance'),
             InlineKeyboardButton("💳 Пополнить", callback_data='deposit')],
            [InlineKeyboardButton("🔮 Предсказание", callback_data='predict'),
             InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("📝 История", callback_data='history')]
        ]
        
        if user.role == UserRole.ADMIN:
            keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data='admin')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"С возвращением, {user.username}!\n"
            f"Ваш баланс: {user.balance} руб.\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📝 Регистрация", callback_data='register'),
             InlineKeyboardButton("🔑 Вход", callback_data='login')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Привет! Я бот для предсказаний. Для начала работы:",
            reply_markup=reply_markup
        )
    session.close()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'balance':
        await balance(update, context)
    elif query.data == 'deposit':
        await deposit(update, context)
    elif query.data == 'predict':
        await predict(update, context)
    elif query.data == 'history':
        await history(update, context)
    elif query.data == 'admin':
        await admin_menu(update, context)
    elif query.data == 'stats':
        await user_stats(update, context)
    elif query.data.startswith('deposit_'):
        await deposit_amount(update, context)
    elif query.data == 'admin_stats':
        await admin_stats(update, context)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик регистрации"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if user:
        await update.callback_query.message.reply_text("Вы уже зарегистрированы!")
        session.close()
        return ConversationHandler.END
    
    await update.callback_query.message.reply_text("Введите желаемое имя пользователя:")
    session.close()
    return REGISTER

async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода имени при регистрации"""
    session = Session()
    username = update.message.text
    
    if session.query(User).filter_by(username=username).first():
        await update.message.reply_text("Это имя пользователя уже занято. Попробуйте другое:")
        session.close()
        return REGISTER
    
    role = UserRole.ADMIN if username == ADMIN_USERNAME else UserRole.REGULAR
    
    new_user = User(
        telegram_id=update.effective_user.id,
        username=username,
        balance=0.0,
        role=role
    )
    session.add(new_user)
    session.commit()  # Сразу коммитим, чтобы получить ID пользователя
    
    # Обновляем статистику
    stats = session.query(SystemStats).first()
    if not stats:
        stats = SystemStats(total_users=1, total_predictions=0, total_revenue=0.0)
        session.add(stats)
    else:
        # Проверяем, что total_users не None перед инкрементом
        if stats.total_users is None:
            stats.total_users = 1
        else:
            stats.total_users += 1
            
    stats.last_updated = datetime.utcnow()
    session.commit()
    
    # Создаем приветственное уведомление
    notification = Notification(
        user_id=new_user.id,
        message="Добро пожаловать в систему предсказаний!"
    )
    session.add(notification)
    session.commit()
    
    await update.message.reply_text(
        f"Регистрация успешна, {username}!\n"
        f"Ваш баланс: {new_user.balance} руб.\n"
        "Используйте /predict для создания предсказания."
    )
    session.close()
    return ConversationHandler.END

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входа"""
    await update.callback_query.message.reply_text("Введите ваше имя пользователя:")
    return LOGIN

async def login_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода имени при входе"""
    session = Session()
    username = update.message.text
    user = session.query(User).filter_by(username=username).first()
    
    if not user:
        await update.message.reply_text("Пользователь не найден. Попробуйте еще раз:")
        session.close()
        return LOGIN
    
    user.telegram_id = update.effective_user.id
    user.last_activity = datetime.utcnow()
    session.commit()
    
    await update.message.reply_text(
        f"Вход выполнен успешно, {username}!\n"
        f"Ваш баланс: {user.balance} руб.\n"
        "Используйте /predict для создания предсказания."
    )
    session.close()
    return ConversationHandler.END

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик проверки баланса"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.callback_query.message.reply_text("Вы не авторизованы. Используйте /register или /login")
        session.close()
        return
    
    await update.callback_query.message.reply_text(f"Ваш баланс: {user.balance} руб.")
    session.close()

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пополнения баланса"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.callback_query.message.reply_text("Вы не авторизованы. Используйте /register или /login")
        session.close()
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("50 руб.", callback_data='deposit_50'),
         InlineKeyboardButton("100 руб.", callback_data='deposit_100')],
        [InlineKeyboardButton("200 руб.", callback_data='deposit_200'),
         InlineKeyboardButton("500 руб.", callback_data='deposit_500')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.reply_text(
        "Выберите сумму для пополнения:",
        reply_markup=reply_markup
    )
    session.close()

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора суммы для пополнения"""
    query = update.callback_query
    amount = float(query.data.split('_')[1])
    
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    user.balance += amount
    
    # Обновляем статистику
    stats = session.query(SystemStats).first()
    if not stats:
        stats = SystemStats()
        session.add(stats)
    stats.total_revenue += amount
    stats.last_updated = datetime.utcnow()
    
    session.commit()
    
    # Создаем уведомление о пополнении
    notification = Notification(
        user_id=user.id,
        message=f"Ваш баланс пополнен на {amount} руб."
    )
    session.add(notification)
    session.commit()
    
    await query.message.reply_text(
        f"Баланс успешно пополнен на {amount} руб.\n"
        f"Текущий баланс: {user.balance} руб."
    )
    session.close()
    return ConversationHandler.END

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания предсказания"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.callback_query.message.reply_text("Вы не авторизованы. Используйте /register или /login")
        session.close()
        return ConversationHandler.END
    
    if user.balance < PREDICTION_COST:
        await update.callback_query.message.reply_text(
            f"Недостаточно средств на балансе. Минимальная стоимость предсказания: {PREDICTION_COST} руб.\n"
            "Используйте /deposit для пополнения баланса."
        )
        session.close()
        return ConversationHandler.END
    
    await update.callback_query.message.reply_text(
        "Введите данные для предсказания (например, текст или числовые значения):"
    )
    session.close()
    return PREDICT

async def make_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания предсказания"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Вы не авторизованы. Используйте /register или /login")
        session.close()
        return ConversationHandler.END
    
    if user.balance < PREDICTION_COST:
        await update.message.reply_text(
            f"Недостаточно средств на балансе. Минимальная стоимость предсказания: {PREDICTION_COST} руб.\n"
            "Используйте /deposit для пополнения баланса."
        )
        session.close()
        return ConversationHandler.END
        
    input_text = update.message.text
    
    # Пытаемся сделать запрос к API
    try:
        # Создаем данные для предсказания
        input_data = {"text": input_text}
        
        # Отправляем запрос в API и сообщаем пользователю
        status_message = await update.message.reply_text("🔄 Отправляю запрос в очередь обработки...")
        
        # Отправляем запрос в API (теперь это отправит задачу в RabbitMQ)
        api_result = await api_predict(input_data)
        
        if "error" in api_result:
            # Если API недоступен, генерируем случайное предсказание
            logger.warning(f"Ошибка API, использую локальное предсказание: {api_result}")
            
            # Обновляем сообщение
            await status_message.edit_text("⚠️ Ошибка API, использую локальное предсказание...")
            
            predictions = [
                ("Да, это произойдет в ближайшее время", 0.85),
                ("Нет, этого не случится", 0.75),
                ("Возможно, но не факт", 0.65),
                ("Скорее всего, да", 0.80),
                ("Скорее всего, нет", 0.70),
                ("Нужно больше информации", 0.50)
            ]
            prediction_text, confidence = random.choice(predictions)
            result = {"prediction": prediction_text, "confidence": confidence}
            worker_id = "local"
        else:
            # Используем результат от API
            logger.info(f"Получен ответ от API: {api_result}")
            
            # Проверяем, завершена ли задача
            if api_result.get("status") == "completed":
                await status_message.edit_text("✅ Задача обработана! Получаю результат...")
            else:
                await status_message.edit_text("⏳ Задача находится в обработке, но время ожидания истекло")
            
            # Извлекаем результат
            if "result" in api_result and isinstance(api_result["result"], dict):
                result_data = api_result["result"].get("result", {})
                if isinstance(result_data, dict):
                    prediction_text = str(result_data.get("prediction", "Неопределенное предсказание"))
                    confidence = float(result_data.get("confidence", 0.5))
                    worker_id = result_data.get("worker_id", "unknown")
                else:
                    prediction_text = "Некорректный формат результата"
                    confidence = 0.5
                    worker_id = "unknown"
            else:
                prediction_text = "Ожидание результата"
                confidence = 0.5
                worker_id = "pending"
                
            result = {"prediction": prediction_text, "confidence": confidence}
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении предсказания: {e}")
        # В случае ошибки генерируем случайное предсказание
        predictions = [
            ("Да, это произойдет в ближайшее время", 0.85),
            ("Нет, этого не случится", 0.75),
            ("Возможно, но не факт", 0.65)
        ]
        prediction_text, confidence = random.choice(predictions)
        result = {"prediction": prediction_text, "confidence": confidence}
        worker_id = "error"
    
    # Создаем предсказание с результатом в JSON формате
    prediction = Prediction(
        user_id=user.id,
        input_data=input_text,
        result=json.dumps(result),  # Сохраняем весь результат как JSON строку
        cost=PREDICTION_COST
    )
    session.add(prediction)
    
    # Списываем средства
    user.balance -= PREDICTION_COST
    
    # Обновляем статистику
    stats = session.query(SystemStats).first()
    if not stats:
        stats = SystemStats()
        session.add(stats)
    
    if stats.total_predictions is None:
        stats.total_predictions = 1
    else:
        stats.total_predictions += 1
    
    stats.last_updated = datetime.utcnow()
    
    session.commit()
    
    # Отправляем результат пользователю
    await update.message.reply_text(
        f"🔮 Предсказание: {result['prediction']}\n"
        f"📊 Уверенность: {result['confidence']*100:.1f}%\n"
        f"🤖 Обработано воркером: {worker_id}\n"
        f"💰 С вашего баланса списано {PREDICTION_COST} руб.\n"
        f"💳 Остаток на балансе: {user.balance} руб."
    )
    session.close()
    return ConversationHandler.END

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик истории предсказаний"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.callback_query.message.reply_text("Вы не авторизованы. Используйте /register или /login")
        session.close()
        return
    
    predictions = session.query(Prediction).filter_by(user_id=user.id).order_by(Prediction.created_at.desc()).limit(5).all()
    
    if not predictions:
        await update.callback_query.message.reply_text("У вас пока нет предсказаний.")
        session.close()
        return
    
    message = "📝 Последние 5 предсказаний:\n\n"
    for pred in predictions:
        # Парсим JSON для получения результата и уверенности
        try:
            result_data = json.loads(pred.result)
            prediction_text = result_data.get("prediction", "Неизвестно")
            confidence = result_data.get("confidence", 0.5)
        except (json.JSONDecodeError, TypeError):
            # Если не удалось распарсить JSON, используем значения по умолчанию
            prediction_text = pred.result
            confidence = 0.5
            
        message += (
            f"📅 {pred.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"📄 Входные данные: {pred.input_data}\n"
            f"🔮 Предсказание: {prediction_text}\n"
            f"📊 Уверенность: {confidence*100:.1f}%\n"
            f"💰 Стоимость: {pred.cost} руб.\n\n"
        )
    
    await update.callback_query.message.reply_text(message)
    session.close()

async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик статистики пользователя"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.callback_query.message.reply_text("Вы не авторизованы. Используйте /register или /login")
        session.close()
        return
    
    # Используем session.execute вместо query для более безопасного SQL
    total_predictions_result = session.execute(
        "SELECT COUNT(*) FROM predictions WHERE user_id = :user_id",
        {"user_id": user.id}
    )
    total_predictions = total_predictions_result.scalar() or 0
    
    total_spent_result = session.execute(
        "SELECT COALESCE(SUM(cost), 0) FROM predictions WHERE user_id = :user_id",
        {"user_id": user.id}
    )
    total_spent = total_spent_result.scalar() or 0.0
    
    await update.callback_query.message.reply_text(
        f"📊 Ваша статистика:\n\n"
        f"👤 Имя пользователя: {user.username}\n"
        f"💰 Текущий баланс: {user.balance} руб.\n"
        f"🔮 Всего предсказаний: {total_predictions}\n"
        f"💸 Всего потрачено: {total_spent} руб.\n"
        f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
    )
    session.close()

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик админ-панели"""
    session = Session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user or user.role != UserRole.ADMIN:
        await update.callback_query.message.reply_text("У вас нет доступа к админ-панели.")
        session.close()
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("👥 Управление пользователями", callback_data='admin_users')],
        [InlineKeyboardButton("🔔 Отправить уведомление", callback_data='admin_notify')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.reply_text(
        "👑 Админ-панель\nВыберите действие:",
        reply_markup=reply_markup
    )
    session.close()
    return ADMIN_MENU

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик статистики системы"""
    session = Session()
    stats = session.query(SystemStats).first()
    
    if not stats:
        stats = SystemStats()
        session.add(stats)
        session.commit()
    
    # Используем безопасные SQL запросы через session.execute
    total_users_result = session.execute("SELECT COUNT(*) FROM users")
    total_users = total_users_result.scalar() or 0
    
    active_users_result = session.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
    active_users = active_users_result.scalar() or 0
    
    total_predictions_result = session.execute("SELECT COUNT(*) FROM predictions")
    total_predictions = total_predictions_result.scalar() or 0
    
    await update.callback_query.message.reply_text(
        f"📊 Статистика системы:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Активных пользователей: {active_users}\n"
        f"🔮 Всего предсказаний: {total_predictions}\n"
        f"💰 Общая выручка: {stats.total_revenue} руб.\n"
        f"🔄 Последнее обновление: {stats.last_updated.strftime('%d.%m.%Y %H:%M')}"
    )
    session.close()

def main():
    """Основная функция запуска бота"""
    try:
        # Настройка HTTP клиента с увеличенными таймаутами
        request = HTTPXRequest(
            connection_pool_size=8,
            read_timeout=60,
            write_timeout=60,
            connect_timeout=60,
            pool_timeout=60
        )
        
        # Создание приложения с настроенным клиентом
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).build()
        
        # Обработчики команд
        application.add_handler(CommandHandler("start", start))
        
        # Обработчики состояний - ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", start), 
                CallbackQueryHandler(register, pattern='^register$'),
                CallbackQueryHandler(login, pattern='^login$'),
                CallbackQueryHandler(deposit, pattern='^deposit$'),
                CallbackQueryHandler(predict, pattern='^predict$'),
                CallbackQueryHandler(admin_menu, pattern='^admin$')
            ],
            states={
                REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
                LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_name)],
                DEPOSIT: [CallbackQueryHandler(deposit_amount, pattern='^deposit_')],
                PREDICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, make_prediction)],
                ADMIN_MENU: [
                    CallbackQueryHandler(admin_stats, pattern='^admin_stats$'),
                    # Другие обработчики для кнопок админ-панели
                ] 
            },
            fallbacks=[CommandHandler("start", start), CallbackQueryHandler(start, pattern='^start$')]
        )
        
        application.add_handler(conv_handler)

        # Отдельный обработчик для кнопок, не входящих в ConversationHandler
        application.add_handler(CallbackQueryHandler(button_handler)) 

        logger.info("Бот запускается...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main() 