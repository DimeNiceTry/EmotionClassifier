"""
Типы и статусы транзакций в системе.
"""
from enum import Enum


class TransactionType(Enum):
    """Типы транзакций в системе."""

    DEPOSIT = "deposit"  # Пополнение баланса
    WITHDRAWAL = "withdrawal"  # Списание за использование ML сервиса


class TransactionStatus(Enum):
    """Статусы транзакций в системе."""

    COMPLETED = "completed"  # Успешно завершенная транзакция
    FAILED = "failed"  # Неудачная транзакция 