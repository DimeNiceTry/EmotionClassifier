"""
Роли пользователей системы.
"""
from typing import Set

from ml_service.models.base.user_role import UserRole


class RegularUserRole(UserRole):
    """Роль обычного пользователя системы."""

    def has_permission(self, permission: str) -> bool:
        """
        Проверить наличие разрешения у обычного пользователя.
        
        Args:
            permission: Название разрешения
            
        Returns:
            True если разрешение есть, иначе False
        """
        # Список разрешений обычного пользователя
        regular_permissions = {
            'view_balance', 
            'top_up_balance', 
            'run_ml_task', 
            'view_history'
        }
        
        return permission in regular_permissions


class AdminRole(UserRole):
    """Роль администратора системы."""

    def has_permission(self, permission: str) -> bool:
        """
        Проверить наличие разрешения у администратора.
        
        Args:
            permission: Название разрешения
            
        Returns:
            True если разрешение есть, иначе False
        """
        # Администратор имеет все разрешения обычного пользователя
        # плюс дополнительные админские разрешения
        regular_role = RegularUserRole()
        
        admin_permissions = {
            'manage_users', 
            'view_all_transactions', 
            'top_up_user_balance',
            'moderate_top_ups'
        }
        
        return regular_role.has_permission(permission) or permission in admin_permissions 