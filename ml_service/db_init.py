"""
Скрипт для инициализации базы данных демо-данными.
"""
import sys
import os
from sqlalchemy.orm import Session

# Добавление корневой директории проекта в sys.path 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml_service.db_config import init_db, SessionLocal
from ml_service.models.users.user_manager import UserManager
from ml_service.models.transactions.transaction_manager import TransactionManager
from ml_service.models.users.roles import AdminRole, RegularUserRole


def init_demo_data(db: Session):
    """
    Инициализация базы данных демо-данными.
    
    Args:
        db: Сессия базы данных
    """
    user_manager = UserManager(db)
    transaction_manager = TransactionManager(db)
    
    # Создаем демо администратора
    try:
        admin = user_manager.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            role=AdminRole()
        )
        print(f"Создан администратор: {admin.username}")
    except ValueError as e:
        print(f"Ошибка создания администратора: {e}")
        admin = user_manager.get_user_by_username("admin")
        print(f"Использован существующий администратор: {admin.username}")
    
    # Создаем демо пользователя
    try:
        demo_user = user_manager.create_user(
            username="demouser",
            email="demo@example.com",
            password="demo123",
            role=RegularUserRole()
        )
        print(f"Создан демо пользователь: {demo_user.username}")
    except ValueError as e:
        print(f"Ошибка создания демо пользователя: {e}")
        demo_user = user_manager.get_user_by_username("demouser")
        print(f"Использован существующий демо пользователь: {demo_user.username}")
    
    # Пополняем баланс демо пользователя
    if demo_user:
        balance = transaction_manager.get_balance(demo_user.id)
        if balance and balance.amount < 1000:
            transaction_manager.top_up_balance(
                user_id=demo_user.id,
                amount=1000,
                description="Демо пополнение баланса"
            )
            print(f"Баланс демо пользователя пополнен на 1000 кредитов")
    
    # Создаем несколько транзакций для демо пользователя
    if demo_user:
        # Списываем средства для создания истории транзакций
        for i in range(3):
            transaction_manager.withdraw_from_balance(
                user_id=demo_user.id,
                amount=100,
                description=f"Демо списание #{i+1}",
                related_entity_id=f"demo_task_{i+1}"
            )
        print(f"Созданы демо транзакции для пользователя {demo_user.username}")


if __name__ == "__main__":
    # Инициализация базы данных (создание таблиц)
    init_db()
    print("База данных инициализирована")
    
    # Создание демо-данных
    db = SessionLocal()
    try:
        init_demo_data(db)
        print("Демо-данные созданы")
    finally:
        db.close() 