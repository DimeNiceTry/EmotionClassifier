from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ml_service")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

def get_db_session():
    """
    Возвращает сессию базы данных для использования в воркерах
    
    Отличается от get_db тем, что использует yield вместо return,
    что позволяет использовать ее в функциях, не являющихся генераторами.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 