"""
Модель баланса пользователя.
"""
from typing import Dict, Any
from datetime import datetime

from ml_service.models.base.entity import Entity


class Balance(Entity):
    """Модель баланса пользователя."""

    def __init__(
        self, 
        user_id: str,
        amount: int = 0,
        id: str = None
    ):
        super().__init__(id)
        self._user_id = user_id
        self._amount = amount

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def amount(self) -> int:
        return self._amount

    def top_up(self, amount: int) -> bool:
        """
        Пополнить баланс пользователя.
        
        Args:
            amount: Сумма пополнения в кредитах
            
        Returns:
            True если операция успешна, иначе False
        """
        if amount <= 0:
            return False
        
        self._amount += amount
        self.update()
        return True

    def withdraw(self, amount: int) -> bool:
        """
        Списать с баланса пользователя.
        
        Args:
            amount: Сумма списания в кредитах
            
        Returns:
            True если операция успешна, иначе False
        """
        if amount <= 0 or self._amount < amount:
            return False
        
        self._amount -= amount
        self.update()
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать баланс в словарь для сериализации.
        
        Returns:
            Словарь с данными баланса
        """
        return {
            'id': self.id,
            'user_id': self._user_id,
            'amount': self._amount,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 