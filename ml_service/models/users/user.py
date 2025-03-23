"""
Модель пользователя системы.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from ml_service.models.base.entity import Entity
from ml_service.models.base.user_role import UserRole
from ml_service.models.users.roles import RegularUserRole


class User(Entity):
    """Модель пользователя системы."""

    def __init__(
        self, 
        username: str, 
        email: str, 
        password_hash: str, 
        role: UserRole = None, 
        balance: int = 0, 
        id: str = None
    ):
        super().__init__(id)
        self._username = username
        self._email = email
        self._password_hash = password_hash
        self._role = role if role else RegularUserRole()
        self._balance = balance
        self._is_active = True
        self._last_login = None

    @property
    def username(self) -> str:
        return self._username

    @property
    def email(self) -> str:
        return self._email

    @property
    def balance(self) -> int:
        return self._balance

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def last_login(self) -> Optional[datetime]:
        return self._last_login

    @property
    def role(self) -> UserRole:
        return self._role

    def verify_password(self, password: str) -> bool:
        """
        Проверить пароль пользователя.
        
        Args:
            password: Пароль для проверки
            
        Returns:
            True если пароль верный, иначе False
        """
        # В реальной системе здесь будет проверка хеша пароля
        # Это заглушка для примера
        return True

    def has_permission(self, permission: str) -> bool:
        """
        Проверить наличие разрешения у пользователя.
        
        Args:
            permission: Название разрешения
            
        Returns:
            True если разрешение есть у роли пользователя, иначе False
        """
        return self._role.has_permission(permission)

    def top_up_balance(self, amount: int) -> bool:
        """
        Пополнить баланс пользователя.
        
        Args:
            amount: Сумма пополнения в кредитах
            
        Returns:
            True если операция успешна, иначе False
        """
        if amount <= 0:
            return False
        
        self._balance += amount
        self.update()
        return True

    def withdraw_balance(self, amount: int) -> bool:
        """
        Списать с баланса пользователя.
        
        Args:
            amount: Сумма списания в кредитах
            
        Returns:
            True если операция успешна, иначе False
        """
        if amount <= 0 or self._balance < amount:
            return False
        
        self._balance -= amount
        self.update()
        return True

    def set_role(self, role: UserRole) -> None:
        """
        Установить роль пользователя.
        
        Args:
            role: Новая роль пользователя
        """
        self._role = role
        self.update()

    def record_login(self) -> None:
        """Записать время последнего входа в систему."""
        self._last_login = datetime.now()
        self.update()

    def activate(self) -> None:
        """Активировать учетную запись пользователя."""
        self._is_active = True
        self.update()

    def deactivate(self) -> None:
        """Деактивировать учетную запись пользователя."""
        self._is_active = False
        self.update()
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразовать пользователя в словарь для сериализации.
        
        Returns:
            Словарь с данными пользователя
        """
        return {
            'id': self.id,
            'username': self._username,
            'email': self._email,
            'role': self._role.__class__.__name__,
            'balance': self._balance,
            'is_active': self._is_active,
            'last_login': self._last_login.isoformat() if self._last_login else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 