"""
Реализации репозиториев с использованием SQLAlchemy.
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from datetime import datetime

from ..domain.models import User as UserDomain
from ..domain.models import UserBalance as UserBalanceDomain
from ..domain.models import Transaction as TransactionDomain
from ..domain.models import Prediction as PredictionDomain
from ..domain.models import PredictionResult, TransactionType, TransactionStatus, PredictionStatus

from ..database.models import User as UserDB
from ..database.models import Balance as BalanceDB
from ..database.models import Transaction as TransactionDB
from ..database.models import Prediction as PredictionDB

from .interfaces import UserRepository, BalanceRepository, TransactionRepository, PredictionRepository


# Вспомогательные функции для конвертации объектов
def db_user_to_domain(db_user: UserDB) -> UserDomain:
    return UserDomain(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        disabled=db_user.disabled,
        created_at=db_user.created_at,
        hashed_password=db_user.hashed_password
    )


def domain_user_to_db(user: UserDomain, db_user: Optional[UserDB] = None) -> UserDB:
    if db_user is None:
        db_user = UserDB()
    
    db_user.username = user.username
    db_user.email = user.email
    db_user.full_name = user.full_name
    db_user.disabled = user.disabled
    if user.hashed_password:
        db_user.hashed_password = user.hashed_password
    
    return db_user


def db_balance_to_domain(db_balance: BalanceDB) -> UserBalanceDomain:
    return UserBalanceDomain(
        user_id=db_balance.user_id,
        amount=db_balance.amount,
        updated_at=db_balance.updated_at
    )


def domain_balance_to_db(balance: UserBalanceDomain, db_balance: Optional[BalanceDB] = None) -> BalanceDB:
    if db_balance is None:
        db_balance = BalanceDB(user_id=balance.user_id)
    
    db_balance.amount = balance.amount
    
    return db_balance


def db_transaction_to_domain(db_transaction: TransactionDB) -> TransactionDomain:
    return TransactionDomain(
        id=db_transaction.id,
        user_id=db_transaction.user_id,
        amount=db_transaction.amount,
        type=TransactionType(db_transaction.type),
        status=TransactionStatus(db_transaction.status),
        created_at=db_transaction.created_at
    )


def domain_transaction_to_db(transaction: TransactionDomain, db_transaction: Optional[TransactionDB] = None) -> TransactionDB:
    if db_transaction is None:
        db_transaction = TransactionDB(user_id=transaction.user_id)
    
    db_transaction.amount = transaction.amount
    db_transaction.type = transaction.type.value
    db_transaction.status = transaction.status.value
    
    return db_transaction


def db_prediction_to_domain(db_prediction: PredictionDB) -> PredictionDomain:
    try:
        input_data = json.loads(db_prediction.input_data)
    except:
        input_data = {}
    
    try:
        result_dict = json.loads(db_prediction.result)
        status = result_dict.get("status", PredictionStatus.PENDING.value)
        prediction_result = PredictionResult(
            result=result_dict,
            status=PredictionStatus(status)
        )
    except:
        prediction_result = PredictionResult()
    
    return PredictionDomain(
        id=db_prediction.id,
        user_id=db_prediction.user_id,
        input_data=input_data,
        result=prediction_result,
        cost=db_prediction.cost,
        created_at=db_prediction.created_at
    )


def domain_prediction_to_db(prediction: PredictionDomain, db_prediction: Optional[PredictionDB] = None) -> PredictionDB:
    if db_prediction is None:
        db_prediction = PredictionDB(user_id=prediction.user_id)
    
    db_prediction.input_data = json.dumps(prediction.input_data)
    db_prediction.result = json.dumps(prediction.result.dict())
    db_prediction.cost = prediction.cost
    
    return db_prediction


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_by_id(self, user_id: int) -> Optional[UserDomain]:
        db_user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
        if db_user:
            return db_user_to_domain(db_user)
        return None
    
    async def get_by_username(self, username: str) -> Optional[UserDomain]:
        db_user = self.db.query(UserDB).filter(UserDB.username == username).first()
        if db_user:
            return db_user_to_domain(db_user)
        return None
    
    async def create(self, user: UserDomain) -> UserDomain:
        db_user = domain_user_to_db(user)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user_to_domain(db_user)
    
    async def update(self, user: UserDomain) -> UserDomain:
        db_user = self.db.query(UserDB).filter(UserDB.id == user.id).first()
        if not db_user:
            raise ValueError(f"User with id {user.id} not found")
        
        db_user = domain_user_to_db(user, db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user_to_domain(db_user)


class SQLAlchemyBalanceRepository(BalanceRepository):
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_by_user_id(self, user_id: int) -> Optional[UserBalanceDomain]:
        db_balance = self.db.query(BalanceDB).filter(BalanceDB.user_id == user_id).first()
        if db_balance:
            return db_balance_to_domain(db_balance)
        return None
    
    async def create(self, balance: UserBalanceDomain) -> UserBalanceDomain:
        db_balance = domain_balance_to_db(balance)
        self.db.add(db_balance)
        self.db.commit()
        self.db.refresh(db_balance)
        return db_balance_to_domain(db_balance)
    
    async def update(self, balance: UserBalanceDomain) -> UserBalanceDomain:
        db_balance = self.db.query(BalanceDB).filter(BalanceDB.user_id == balance.user_id).first()
        if not db_balance:
            raise ValueError(f"Balance for user_id {balance.user_id} not found")
        
        db_balance = domain_balance_to_db(balance, db_balance)
        self.db.commit()
        self.db.refresh(db_balance)
        return db_balance_to_domain(db_balance)


class SQLAlchemyTransactionRepository(TransactionRepository):
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_by_id(self, transaction_id: int) -> Optional[TransactionDomain]:
        db_transaction = self.db.query(TransactionDB).filter(TransactionDB.id == transaction_id).first()
        if db_transaction:
            return db_transaction_to_domain(db_transaction)
        return None
    
    async def get_by_user_id(self, user_id: int) -> List[TransactionDomain]:
        db_transactions = self.db.query(TransactionDB).filter(
            TransactionDB.user_id == user_id
        ).order_by(TransactionDB.created_at.desc()).all()
        
        return [db_transaction_to_domain(t) for t in db_transactions]
    
    async def create(self, transaction: TransactionDomain) -> TransactionDomain:
        db_transaction = domain_transaction_to_db(transaction)
        self.db.add(db_transaction)
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction_to_domain(db_transaction)
    
    async def update(self, transaction: TransactionDomain) -> TransactionDomain:
        db_transaction = self.db.query(TransactionDB).filter(TransactionDB.id == transaction.id).first()
        if not db_transaction:
            raise ValueError(f"Transaction with id {transaction.id} not found")
        
        db_transaction = domain_transaction_to_db(transaction, db_transaction)
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction_to_domain(db_transaction)


class SQLAlchemyPredictionRepository(PredictionRepository):
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_by_id(self, prediction_id: int) -> Optional[PredictionDomain]:
        db_prediction = self.db.query(PredictionDB).filter(PredictionDB.id == prediction_id).first()
        if db_prediction:
            return db_prediction_to_domain(db_prediction)
        return None
    
    async def get_by_user_id(self, user_id: int) -> List[PredictionDomain]:
        db_predictions = self.db.query(PredictionDB).filter(
            PredictionDB.user_id == user_id
        ).order_by(PredictionDB.created_at.desc()).all()
        
        return [db_prediction_to_domain(p) for p in db_predictions]
    
    async def create(self, prediction: PredictionDomain) -> PredictionDomain:
        db_prediction = domain_prediction_to_db(prediction)
        self.db.add(db_prediction)
        self.db.commit()
        self.db.refresh(db_prediction)
        return db_prediction_to_domain(db_prediction)
    
    async def update(self, prediction: PredictionDomain) -> PredictionDomain:
        db_prediction = self.db.query(PredictionDB).filter(PredictionDB.id == prediction.id).first()
        if not db_prediction:
            raise ValueError(f"Prediction with id {prediction.id} not found")
        
        db_prediction = domain_prediction_to_db(prediction, db_prediction)
        self.db.commit()
        self.db.refresh(db_prediction)
        return db_prediction_to_domain(db_prediction) 