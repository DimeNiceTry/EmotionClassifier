"""
Сервисы для Telegram бота.
"""

from services.bot.services.db_service import (
    get_db_connection,
    wait_for_db,
    register_user,
    get_user_balance
)

from services.bot.services.rabbitmq_service import (
    get_rabbitmq_connection,
    wait_for_rabbitmq, 
    publish_message,
    ML_TASK_QUEUE,
    ML_RESULT_QUEUE
)

from services.bot.services.prediction_service import (
    create_prediction,
    get_prediction_status,
    get_user_predictions
)

__all__ = [
    # Сервис базы данных
    "get_db_connection",
    "wait_for_db",
    "register_user",
    "get_user_balance",
    
    # Сервис RabbitMQ
    "get_rabbitmq_connection",
    "wait_for_rabbitmq",
    "publish_message",
    "ML_TASK_QUEUE",
    "ML_RESULT_QUEUE",
    
    # Сервис предсказаний
    "create_prediction",
    "get_prediction_status",
    "get_user_predictions"
] 