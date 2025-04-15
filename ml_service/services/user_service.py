"""
Сервис для работы с пользователями и их балансом.
"""
from typing import List, Optional, Dict
from ..domain.models import User, UserBalance, Transaction, TransactionType, TransactionStatus
from ..repositories.interfaces import UserRepository, BalanceRepository, TransactionRepository


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        balance_repository: BalanceRepository,
        transaction_repository: TransactionRepository
    ):
        self.user_repository = user_repository
        self.balance_repository = balance_repository
        self.transaction_repository = transaction_repository
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        return await self.user_repository.get_by_id(user_id)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по имени пользователя"""
        return await self.user_repository.get_by_username(username)
    
    async def create_user(self, user: User) -> User:
        """Создать нового пользователя"""
        created_user = await self.user_repository.create(user)
        
        # Создаем начальный баланс для пользователя
        await self.balance_repository.create(UserBalance(user_id=created_user.id, amount=0.0))
        
        return created_user
    
    async def update_user(self, user: User) -> User:
        """Обновить данные пользователя"""
        return await self.user_repository.update(user)
    
    async def get_user_balance(self, user_id: int) -> float:
        """Получить баланс пользователя"""
        balance = await self.balance_repository.get_by_user_id(user_id)
        if not balance:
            raise ValueError(f"Balance for user_id {user_id} not found")
        return balance.amount
    
    async def deposit_funds(self, user_id: int, amount: float) -> Transaction:
        """Пополнить баланс пользователя"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED
        )
        transaction = await self.transaction_repository.create(transaction)
        
        # Обновляем баланс
        balance = await self.balance_repository.get_by_user_id(user_id)
        if not balance:
            balance = UserBalance(user_id=user_id, amount=0.0)
            balance = await self.balance_repository.create(balance)
        else:
            balance.amount += amount
            balance = await self.balance_repository.update(balance)
        
        return transaction
    
    async def withdraw_funds(self, user_id: int, amount: float) -> Optional[Transaction]:
        """Списать средства с баланса пользователя"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Проверяем баланс
        balance = await self.balance_repository.get_by_user_id(user_id)
        if not balance or balance.amount < amount:
            raise ValueError("Insufficient balance")
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED
        )
        transaction = await self.transaction_repository.create(transaction)
        
        # Обновляем баланс
        balance.amount -= amount
        await self.balance_repository.update(balance)
        
        return transaction
    
    async def get_transaction_history(self, user_id: int) -> List[Transaction]:
        """Получить историю транзакций пользователя"""
        return await self.transaction_repository.get_by_user_id(user_id) 