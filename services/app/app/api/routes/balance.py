"""
Маршруты для работы с балансом пользователя.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.users import User
from app.schemas.balances import BalanceTopUpRequest, BalanceTopUpResponse
from app.services.balances import get_user_balance, top_up_balance

router = APIRouter(prefix="/balance", tags=["balance"])

@router.get("/")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить текущий баланс пользователя.
    """
    balance = get_user_balance(db, current_user.id)
    return {"balance": balance.amount}

@router.post("/topup", response_model=BalanceTopUpResponse)
async def top_up_user_balance(
    request: BalanceTopUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Пополнить баланс пользователя.
    """
    if request.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сумма пополнения должна быть положительной"
        )
    
    previous_balance, current_balance, transaction_id = top_up_balance(
        db, current_user.id, request.amount
    )
    
    return BalanceTopUpResponse(
        previous_balance=previous_balance,
        current_balance=current_balance,
        transaction_id=transaction_id
    ) 