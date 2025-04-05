"""
Базовый абстрактный класс для всех сущностей системы.
"""
from abc import ABC
from datetime import datetime
import uuid
from typing import Dict, Any


class Entity(ABC):
    """Базовый абстрактный класс для всех сущностей системы."""

    def __init__(self, id: str = None):
        self._id = id if id else str(uuid.uuid4())
        self._created_at = datetime.now()
        self._updated_at = datetime.now()

    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(self) -> None:
        """Обновить временную метку последнего изменения."""
        self._updated_at = datetime.now() 