"""
Модель транзакции по счету пользователя.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from ml_service.models.base.entity import Entity
from ml_service.models.transactions.transaction_types import TransactionType, TransactionStatus


class Transaction(Entity):
    """Модель транзакции по счету пользователя."""

    def __init__(
        self, 
        user_id: str, 
        amount: int, 
        transaction_type: TransactionType,
        status: TransactionStatus = TransactionStatus.PENDING,
        description: str = None,
        related_entity_id: str = None,  # Например, ID задачи ML или администратора
        id: str = None
    ):
        super().__init__(id)
        self._user_id = user_id
        self._amount = amount
        self._transaction_type = transaction_type
        self._status = status
        self._description = description
        self._related_entity_id = related_entity_id
        self._completed_at = None
        self._error_message = None

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type

    @property
    def status(self) -> TransactionStatus:
        return self._status

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def related_entity_id(self) -> Optional[str]:
        return self._related_entity_id

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    def mark_as_completed(self) -> None:
        """Отметить транзакцию как успешно завершенную."""
        self._status = TransactionStatus.COMPLETED
        self._completed_at = datetime.now()
        self.update()

    def mark_as_failed(self, error_message: str) -> None:
        """
        Отметить транзакцию как неудачную.
        
        Args:
            error_message: Сообщение об ошибке
        """
        self._status = TransactionStatus.FAILED
        self._error_message = error_message
        self._completed_at = datetime.now()
        self.update()

    def cancel(self, reason: str = None) -> None:
        """
        Отменить транзакцию.
        
        Args:
            reason: Причина отмены
        """
        self._status = TransactionStatus.CANCELLED
        self._error_message = reason
        self._completed_at = datetime.now()
        self.update()

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать транзакцию в словарь для сериализации.
        
        Returns:
            Словарь с данными транзакции
        """
        return {
            'id': self.id,
            'user_id': self._user_id,
            'amount': self._amount,
            'transaction_type': self._transaction_type.value,
            'status': self._status.value,
            'description': self._description,
            'related_entity_id': self._related_entity_id,
            'completed_at': self._completed_at.isoformat() if self._completed_at else None,
            'error_message': self._error_message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 