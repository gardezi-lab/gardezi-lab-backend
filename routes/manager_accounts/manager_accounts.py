from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from typing import List

from models.models import ManagerAccount
from schemas.schemas import ManagerAccountCreate, ManagerAccountResponse
from database.database import get_db

router = APIRouter(prefix="/manager-accounts", tags=["Manager Accounts"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)


# ✅ Create Manager Account
@router.post("/", response_model=ManagerAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_manager_account(request: ManagerAccountCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(ManagerAccount).where(ManagerAccount.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_account = ManagerAccount(
        name=request.name,
        about=request.about,
        username=request.username,
        password=hash_password(request.password)
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    return new_account


# ✅ Get All Manager Accounts
@router.get("/", response_model=List[ManagerAccountResponse])
async def get_manager_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ManagerAccount))
    return result.scalars().all()


# ✅ Get Manager Account by ID
@router.get("/{id}", response_model=ManagerAccountResponse)
async def get_manager_account(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ManagerAccount).where(ManagerAccount.id == id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Manager account not found")
    return account


# ✅ Update Manager Account
@router.put("/{id}", response_model=ManagerAccountResponse)
async def update_manager_account(id: int, request: ManagerAccountCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ManagerAccount).where(ManagerAccount.id == id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Manager account not found")

    account.name = request.name
    account.about = request.about
    account.username = request.username
    account.password = hash_password(request.password)

    await db.commit()
    await db.refresh(account)
    return account


# ✅ Delete Manager Account
@router.delete("/{id}")
async def delete_manager_account(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ManagerAccount).where(ManagerAccount.id == id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Manager account not found")

    await db.delete(account)
    await db.commit()
    return {"detail": "Manager account deleted successfully"}
