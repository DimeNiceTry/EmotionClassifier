from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime
from ..services.dependencies import get_user_service
from ..services.user_service import UserService
from ..domain.models import User, Transaction, TransactionType, TransactionStatus
from .auth import get_current_user, oauth2_scheme
from .models import UserBalance, TransactionResponse, TransactionHistory

router = APIRouter()

@router.get("/balance", response_model=UserBalance)
async def get_user_balance(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        balance = await user_service.get_user_balance(current_user.id)
        return UserBalance(balance=balance)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/deposit")
async def deposit_funds(
    amount: float,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    try:
        transaction = await user_service.deposit_funds(current_user.id, amount)
        
        transaction_response = TransactionResponse(
            transaction_id=transaction.id,
            amount=transaction.amount,
            type=transaction.type.value,
            timestamp=transaction.created_at,
            status=transaction.status.value
        )
        
        return {
            "message": "Deposit successful",
            "transaction": transaction_response
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/transactions", response_model=TransactionHistory)
async def get_transaction_history(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    transactions = await user_service.get_transaction_history(current_user.id)
    
    # Конвертируем доменные объекты в DTO для ответа
    transaction_responses = [
        TransactionResponse(
            transaction_id=t.id,
            amount=t.amount,
            type=t.type.value,
            timestamp=t.created_at,
            status=t.status.value
        ) for t in transactions
    ]
    
    return TransactionHistory(transactions=transaction_responses) 