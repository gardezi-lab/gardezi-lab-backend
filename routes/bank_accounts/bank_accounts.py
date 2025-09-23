from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from models.models import BankAccount
from schemas.schemas import BankAccountCreate, BankAccountResponse
from database.database import get_db

router = APIRouter(prefix="/bank-accounts", tags=["Bank Accounts"])


# ✅ Create Bank Account
@router.post("/", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account(request: BankAccountCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(BankAccount).where(BankAccount.account_no == request.account_no))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Account number already exists")

    new_account = BankAccount(
        bank_name=request.bank_name,
        account_no=request.account_no,
        branch=request.branch
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    return new_account


# ✅ Get All Bank Accounts
@router.get("/", response_model=List[BankAccountResponse])
async def get_bank_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount))
    return result.scalars().all()


# ✅ Get Bank Account by ID
@router.get("/{id}", response_model=BankAccountResponse)
async def get_bank_account(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.id == id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return account


# ✅ Update Bank Account
@router.put("/{id}", response_model=BankAccountResponse)
async def update_bank_account(id: int, request: BankAccountCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.id == id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    account.bank_name = request.bank_name
    account.account_no = request.account_no
    account.branch = request.branch

    await db.commit()
    await db.refresh(account)
    return account


# ✅ Delete Bank Account
@router.delete("/{id}")
async def delete_bank_account(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.id == id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    await db.delete(account)
    await db.commit()
    return {"detail": "Bank account deleted successfully"}
