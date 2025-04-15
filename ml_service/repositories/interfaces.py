"""
Интерфейсы репозиториев определяют контракты для работы с данными.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..domain.models import User, UserBalance, Transaction, Prediction


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        pass
        
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        pass
        
    @abstractmethod
    async def create(self, user: User) -> User:
        pass
        
    @abstractmethod
    async def update(self, user: User) -> User:
        pass


class BalanceRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> Optional[UserBalance]:
        pass
        
    @abstractmethod
    async def create(self, balance: UserBalance) -> UserBalance:
        pass
        
    @abstractmethod
    async def update(self, balance: UserBalance) -> UserBalance:
        pass


class TransactionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        pass
        
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Transaction]:
        pass
        
    @abstractmethod
    async def create(self, transaction: Transaction) -> Transaction:
        pass
        
    @abstractmethod
    async def update(self, transaction: Transaction) -> Transaction:
        pass


class PredictionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, prediction_id: int) -> Optional[Prediction]:
        pass
        
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Prediction]:
        pass
        
    @abstractmethod
    async def create(self, prediction: Prediction) -> Prediction:
        pass
        
    @abstractmethod
    async def update(self, prediction: Prediction) -> Prediction:
        pass 