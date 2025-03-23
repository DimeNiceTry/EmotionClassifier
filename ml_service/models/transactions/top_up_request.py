"""
Модель запроса на пополнение баланса.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from ml_service.models.base.entity import Entity


class TopUpRequest(Entity):
    """Модель запроса на пополнение баланса, требующего модерации администратором."""

    def __init__(
        self, 
        user_id: str, 
        amount: int, 
        status: str = "pending",  # pending, approved, rejected
        admin_id: str = None,
        comment: str = None,
        id: str = None
    ):
        super().__init__(id)
        self._user_id = user_id
        self._amount = amount
        self._status = status
        self._admin_id = admin_id
        self._comment = comment
        self._processed_at = None

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def status(self) -> str:
        return self._status

    @property
    def admin_id(self) -> Optional[str]:
        return self._admin_id

    @property
    def comment(self) -> Optional[str]:
        return self._comment

    @property
    def processed_at(self) -> Optional[datetime]:
        return self._processed_at

    def approve(self, admin_id: str, comment: str = None) -> None:
        """
        Одобрить запрос на пополнение баланса.
        
        Args:
            admin_id: ID администратора, одобрившего запрос
            comment: Комментарий администратора (опционально)
        """
        self._status = "approved"
        self._admin_id = admin_id
        self._comment = comment
        self._processed_at = datetime.now()
        self.update()

    def reject(self, admin_id: str, comment: str = None) -> None:
        """
        Отклонить запрос на пополнение баланса.
        
        Args:
            admin_id: ID администратора, отклонившего запрос
            comment: Комментарий администратора (опционально)
        """
        self._status = "rejected"
        self._admin_id = admin_id
        self._comment = comment
        self._processed_at = datetime.now()
        self.update()

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать запрос на пополнение в словарь для сериализации.
        
        Returns:
            Словарь с данными запроса
        """
        return {
            'id': self.id,
            'user_id': self._user_id,
            'amount': self._amount,
            'status': self._status,
            'admin_id': self._admin_id,
            'comment': self._comment,
            'processed_at': self._processed_at.isoformat() if self._processed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 