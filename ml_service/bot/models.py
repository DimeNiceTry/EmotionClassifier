from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
import os
from dotenv import load_dotenv

Base = declarative_base()

class UserRole(enum.Enum):
    REGULAR = "regular"
    ADMIN = "admin"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    balance = Column(Float, default=0.0)
    role = Column(Enum(UserRole), default=UserRole.REGULAR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    predictions = relationship("Prediction", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class Prediction(Base):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    input_data = Column(String)
    result = Column(String)  # JSON строка с результатом и уверенностью
    cost = Column(Float, default=10.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="predictions")

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    message = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")

class SystemStats(Base):
    __tablename__ = 'system_stats'
    
    id = Column(Integer, primary_key=True)
    total_users = Column(Integer, default=0)
    total_predictions = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

# Загрузка переменных окружения
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

# Получение URL базы данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Создание базы данных
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine) 