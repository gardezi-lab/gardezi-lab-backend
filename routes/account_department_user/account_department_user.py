from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from typing import List

from models.models import AccountDepartmentUser
from schemas.schemas import AccountDepartmentUserCreate, AccountDepartmentUserResponse
from database.database import get_db

router = APIRouter(prefix="/account-users", tags=["Account Users"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)


# ✅ Create Account User
@router.post("/", response_model=AccountDepartmentUserResponse, status_code=status.HTTP_201_CREATED)
async def create_account_user(request: AccountDepartmentUserCreate, db: AsyncSession = Depends(get_db)):
    # check if username already exists
    existing = await db.execute(select(AccountDepartmentUser).where(AccountDepartmentUser.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = AccountDepartmentUser(
        name=request.name,
        description=request.description,
        username=request.username,
        password=hash_password(request.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# ✅ Get All Users
@router.get("/", response_model=List[AccountDepartmentUserResponse])
async def get_account_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AccountDepartmentUser))
    return result.scalars().all()


# ✅ Get User by ID
@router.get("/{id}", response_model=AccountDepartmentUserResponse)
async def get_account_user(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AccountDepartmentUser).where(AccountDepartmentUser.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ✅ Update User
@router.put("/{id}", response_model=AccountDepartmentUserResponse)
async def update_account_user(id: int, request: AccountDepartmentUserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AccountDepartmentUser).where(AccountDepartmentUser.id == id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.name = request.name
    user.description = request.description
    user.username = request.username
    user.password = hash_password(request.password)

    await db.commit()
    await db.refresh(user)
    return user


# ✅ Delete User
@router.delete("/{id}")
async def delete_account_user(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AccountDepartmentUser).where(AccountDepartmentUser.id == id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"detail": "User deleted successfully"}
