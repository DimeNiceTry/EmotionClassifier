"""
Абстрактный класс для ролей пользователей.
"""
from abc import ABC, abstractmethod


class UserRole(ABC):
    """Абстрактный класс для ролей пользователей."""

    @abstractmethod
    def has_permission(self, permission: str) -> bool:
        """
        Проверить наличие разрешения у роли.
        
        Args:
            permission: Название разрешения
            
        Returns:
            True если разрешение есть, иначе False
        """
        pass 