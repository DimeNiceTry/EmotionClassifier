"""
Конфигурация и инициализация базы данных.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

# База данных SQLite, хранится в файле ml_service.db
DATABASE_URL = "sqlite:///ml_service.db"

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}, # Это нужно только для SQLite
    echo=False, # Установите True для отладки SQL запросов
)

# Создаем базовый класс для наших моделей
Base = declarative_base()

# Создаем фабрику сессий
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем обертку сессии, которая привязана к текущему потоку
SessionLocal = scoped_session(session_factory)

# Функция для получения сессии базы данных
def get_db_session():
    """
    Создает и возвращает новую сессию базы данных.
    
    Yields:
        Сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для инициализации базы данных
def init_db():
    """
    Создает все таблицы в базе данных.
    """
    Base.metadata.create_all(bind=engine) 