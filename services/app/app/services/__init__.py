"""
Сервисные функции для работы с данными.
"""
from services.app.app.services.db_service import (
    get_db_connection, get_db, wait_for_db, create_database, init_db
)
from services.app.app.services.auth_service import (
    get_current_user, create_access_token, verify_password, authenticate_user
)
from services.app.app.services.user_service import (
    create_user, get_user_by_username, get_user_by_id
)
from services.app.app.services.prediction_service import (
    create_prediction, get_prediction, get_user_predictions, create_prediction_orm
)
from services.app.app.services.transaction_service import (
    get_balance, top_up_balance, deduct_from_balance, get_user_transactions
)
from services.app.app.services.rabbitmq_service import (
    get_rabbitmq_connection, wait_for_rabbitmq, publish_message
)

__all__ = [
    "get_db_connection", "get_db", "wait_for_db", "create_database", "init_db",
    "get_current_user", "create_access_token", "verify_password", "authenticate_user",
    "create_user", "get_user_by_username", "get_user_by_id",
    "create_prediction", "get_prediction", "get_user_predictions", "create_prediction_orm",
    "get_balance", "top_up_balance", "deduct_from_balance", "get_user_transactions",
    "get_rabbitmq_connection", "wait_for_rabbitmq", "publish_message"
] 