from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from typing import List

from models.models import Pathologist, Department
from schemas.schemas import PathologistCreate, PathologistResponse
from database.database import get_db

router = APIRouter(prefix="/pathologists", tags=["Pathologists"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)


# ✅ Create Pathologist
@router.post("/", response_model=PathologistResponse, status_code=status.HTTP_201_CREATED)
async def create_pathologist(request: PathologistCreate, db: AsyncSession = Depends(get_db)):
    # Check if username already exists
    existing = await db.execute(select(Pathologist).where(Pathologist.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Fetch departments
    result = await db.execute(select(Department).where(Department.id.in_(request.department_ids)))
    departments = result.scalars().all()
    if not departments:
        raise HTTPException(status_code=400, detail="Invalid department IDs")

    new_pathologist = Pathologist(
        name=request.name,
        description=request.description,
        username=request.username,
        password=hash_password(request.password),
        color_graphical=request.color_graphical,
        departments=departments
    )
    db.add(new_pathologist)
    await db.commit()

    # Reload with departments eagerly
    result = await db.execute(
        select(Pathologist)
        .where(Pathologist.id == new_pathologist.id)
        .options(selectinload(Pathologist.departments))
    )
    return result.scalar_one()


# ✅ Get All Pathologists
@router.get("/", response_model=List[PathologistResponse])
async def get_pathologists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Pathologist).options(selectinload(Pathologist.departments))
    )
    return result.scalars().all()


# ✅ Get Pathologist by ID
@router.get("/{id}", response_model=PathologistResponse)
async def get_pathologist(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Pathologist)
        .where(Pathologist.id == id)
        .options(selectinload(Pathologist.departments))
    )
    pathologist = result.scalar_one_or_none()
    if not pathologist:
        raise HTTPException(status_code=404, detail="Pathologist not found")
    return pathologist


# ✅ Update Pathologist
@router.put("/{id}", response_model=PathologistResponse)
async def update_pathologist(id: int, request: PathologistCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Pathologist)
        .where(Pathologist.id == id)
        .options(selectinload(Pathologist.departments))
    )
    pathologist = result.scalar_one_or_none()

    if not pathologist:
        raise HTTPException(status_code=404, detail="Pathologist not found")

    # Check if username is already taken (by another user)
    existing = await db.execute(
        select(Pathologist).where(Pathologist.username == request.username, Pathologist.id != id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Fetch new departments
    result = await db.execute(select(Department).where(Department.id.in_(request.department_ids)))
    departments = result.scalars().all()
    if not departments:
        raise HTTPException(status_code=400, detail="Invalid department IDs")

    pathologist.name = request.name
    pathologist.description = request.description
    pathologist.username = request.username
    pathologist.password = hash_password(request.password)
    pathologist.color_graphical = request.color_graphical
    pathologist.departments = departments

    await db.commit()

    # Reload with departments eagerly
    result = await db.execute(
        select(Pathologist)
        .where(Pathologist.id == id)
        .options(selectinload(Pathologist.departments))
    )
    return result.scalar_one()


# ✅ Delete Pathologist
@router.delete("/{id}")
async def delete_pathologist(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pathologist).where(Pathologist.id == id))
    pathologist = result.scalar_one_or_none()

    if not pathologist:
        raise HTTPException(status_code=404, detail="Pathologist not found")

    await db.delete(pathologist)
    await db.commit()
    return {"detail": "Pathologist deleted successfully"}
