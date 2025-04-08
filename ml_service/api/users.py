from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from ..database.database import get_db
from ..database.models import User, Balance, Transaction
from .auth import get_current_user

router = APIRouter()

class UserBalance(BaseModel):
    balance: float

class TransactionResponse(BaseModel):
    transaction_id: int
    amount: float
    type: str
    timestamp: datetime
    status: str

    class Config:
        from_attributes = True

class TransactionHistory(BaseModel):
    transactions: List[TransactionResponse]

@router.get("/balance", response_model=UserBalance)
async def get_user_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    balance = db.query(Balance).filter(Balance.user_id == current_user.id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")
    return UserBalance(balance=balance.amount)

@router.post("/deposit")
async def deposit_funds(
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be positive"
        )
    
    # Создаем транзакцию
    transaction = Transaction(
        user_id=current_user.id,
        amount=amount,
        type="deposit",
        status="completed"
    )
    db.add(transaction)
    
    # Обновляем баланс
    balance = db.query(Balance).filter(Balance.user_id == current_user.id).first()
    if not balance:
        balance = Balance(user_id=current_user.id, amount=0.0)
        db.add(balance)
    
    balance.amount += amount
    db.commit()
    
    # Создаем ответ без использования from_orm
    transaction_response = {
        "transaction_id": transaction.id,
        "amount": transaction.amount,
        "type": transaction.type,
        "timestamp": transaction.created_at,
        "status": transaction.status
    }
    
    return {
        "message": "Deposit successful",
        "transaction": transaction_response
    }

@router.get("/transactions", response_model=TransactionHistory)
async def get_transaction_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).all()
    
    return TransactionHistory(
        transactions=[{
            "transaction_id": t.id,
            "amount": t.amount,
            "type": t.type,
            "timestamp": t.created_at,
            "status": t.status
        } for t in transactions]
    ) 