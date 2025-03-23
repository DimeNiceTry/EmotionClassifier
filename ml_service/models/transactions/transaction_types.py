"""
Типы и статусы транзакций в системе.
"""
from enum import Enum


class TransactionType(Enum):
    """Типы транзакций в системе."""

    DEPOSIT = "deposit"  # Пополнение баланса
    WITHDRAWAL = "withdrawal"  # Списание за использование ML сервиса
    REFUND = "refund"  # Возврат кредитов
    ADMIN_ADJUSTMENT = "admin_adjustment"  # Административная корректировка


class TransactionStatus(Enum):
    """Статусы транзакций в системе."""

    PENDING = "pending"  # Ожидающая транзакция
    COMPLETED = "completed"  # Успешно завершенная транзакция
    FAILED = "failed"  # Неудачная транзакция
    CANCELLED = "cancelled"  # Отмененная транзакция 