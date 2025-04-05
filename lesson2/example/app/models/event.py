from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User

@dataclass
class Event:
    """
    Класс для представления события.
    
    Attributes:
        id (int): Уникальный идентификатор события
        title (str): Название события
        image (str): Путь к изображению события
        description (str): Описание события
        creator (User): Создатель события
    """
    id: int
    title: str
    image: str
    description: str
    creator: 'User'

    def __post_init__(self) -> None:
        self._validate_title()
        self._validate_description()

    def _validate_title(self) -> None:
        """Проверяет длину названия события."""
        if not 1 <= len(self.title) <= 100:
            raise ValueError("Title must be between 1 and 100 characters")

    def _validate_description(self) -> None:
        """Проверяет длину описания события."""
        if len(self.description) > 500:
            raise ValueError("Description must not exceed 500 characters")

