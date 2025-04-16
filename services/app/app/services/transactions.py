"""
Сервис для работы с транзакциями и балансом пользователей.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ml_service.models.transactions.balance import Balance
from ml_service.models.transactions.transaction import Transaction
from ml_service.models.transactions.transaction_types import TransactionType, TransactionStatus

# Настройка логирования
logger = logging.getLogger(__name__)


def get_balance(db: Session, user_id: str):
    """
    Получает баланс пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
    
    Returns:
        Balance или None: Объект баланса или None, если баланс не найден
    """
    return db.query(Balance).filter(Balance.user_id == user_id).first()


def top_up_balance(db: Session, user_id: str, amount: float):
    """
    Пополняет баланс пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма пополнения
        
    Returns:
        tuple: (предыдущий баланс, текущий баланс, ID транзакции)
        
    Raises:
        ValueError: Если сумма пополнения отрицательная или возникла ошибка в БД
    """
    if amount <= 0:
        raise ValueError("Сумма пополнения должна быть положительной")
    
    try:
        # Получаем текущий баланс
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            # Если баланс не найден, создаем новый
            balance = Balance(user_id=user_id, amount=0)
            db.add(balance)
            db.flush()
        
        # Запоминаем предыдущий баланс
        previous_balance = balance.amount
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=int(amount * 100),  # Храним в копейках/центах
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=f"Пополнение баланса на {amount}"
        )
        
        db.add(transaction)
        
        # Обновляем баланс
        balance.amount += amount
        
        db.commit()
        db.refresh(balance)
        db.refresh(transaction)
        
        logger.info(f"Баланс пользователя {user_id} пополнен на {amount}")
        return (previous_balance, balance.amount, transaction.id)
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Ошибка при пополнении баланса: {e}")
        raise ValueError("Ошибка при пополнении баланса")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при пополнении баланса: {e}")
        raise


def deduct_from_balance(db: Session, user_id: str, amount: float, description: str, related_entity_id: str = None):
    """
    Списывает средства с баланса пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        amount: Сумма списания
        description: Описание транзакции
        related_entity_id: ID связанной сущности (например, ID предсказания)
    
    Returns:
        tuple: (предыдущий баланс, текущий баланс, ID транзакции)
        
    Raises:
        ValueError: Если недостаточно средств или возникла ошибка в БД
    """
    if amount <= 0:
        raise ValueError("Сумма списания должна быть положительной")
    
    try:
        # Получаем текущий баланс
        balance = db.query(Balance).filter(Balance.user_id == user_id).first()
        
        if not balance:
            raise ValueError("Баланс пользователя не найден")
        
        # Проверяем достаточно ли средств
        if balance.amount < amount:
            raise ValueError("Недостаточно средств на балансе")
        
        # Запоминаем предыдущий баланс
        previous_balance = balance.amount
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=int(amount * 100),  # Храним в копейках/центах
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            description=description,
            related_entity_id=related_entity_id
        )
        
        db.add(transaction)
        
        # Обновляем баланс
        balance.amount -= amount
        
        db.commit()
        db.refresh(balance)
        db.refresh(transaction)
        
        logger.info(f"С баланса пользователя {user_id} списано {amount}")
        return (previous_balance, balance.amount, transaction.id)
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Ошибка при списании с баланса: {e}")
        raise ValueError("Ошибка при списании с баланса")
    
    except ValueError as e:
        db.rollback()
        logger.error(f"Ошибка при списании с баланса: {e}")
        raise
    
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при списании с баланса: {e}")
        raise


def get_user_transactions(db: Session, user_id: str, skip: int = 0, limit: int = 100):
    """
    Получает историю транзакций пользователя.
    
    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Количество записей для пропуска
        limit: Максимальное количество возвращаемых записей
    
    Returns:
        List[Transaction]: Список транзакций
    """
    return db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(
        Transaction.created_at.desc()
    ).offset(skip).limit(limit).all() 