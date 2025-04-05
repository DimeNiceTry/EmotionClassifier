from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from models.event import Event

@dataclass
class User:
    """
    Класс для представления пользователя в системе.
    
    Attributes:
        id (int): Уникальный идентификатор пользователя
        email (str): Email пользователя
        password (str): Пароль пользователя
        events (List[Event]): Список событий пользователя
    """
    id: int
    email: str
    password: str
    events: List['Event'] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate_email()
        self._validate_password()

    def _validate_email(self) -> None:
        """Проверяет корректность email."""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(self.email):
            raise ValueError("Invalid email format")

    def _validate_password(self) -> None:
        """Проверяет минимальную длину пароля."""
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters long")

    def add_event(self, event: 'Event') -> None:
        """Добавляет событие в список событий пользователя."""
        self.events.append(event)

