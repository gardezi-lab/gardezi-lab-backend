from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_
from models.models import Department
from schemas.schemas import DepartmentCreate, DepartmentResponse
from database.database import get_db

router = APIRouter(prefix="/department", tags=["Department"])


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(request: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    new_dept = Department(**request.dict())
    db.add(new_dept)
    await db.commit()
    await db.refresh(new_dept)
    return new_dept


@router.get("/", response_model=list[DepartmentResponse])
async def get_all_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department))
    return result.scalars().all()


# ✅ Searching route (name/code/description etc.)
@router.get("/search/", response_model=list[DepartmentResponse])
async def search_departments(
    searchbyname: str,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Department)
        .where(
            or_(
                Department.name.ilike(f"%{searchbyname}%"),
                Department.code.ilike(f"%{searchbyname}%"),       # agar `code` field hai
    
            )
        )
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{id}", response_model=DepartmentResponse)
async def get_department(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.put("/{id}")
async def update_department(id: int, request: DepartmentCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.execute(update(Department).where(Department.id == id).values(**request.dict()))
    await db.commit()
    return {"detail": "Department updated successfully"}


@router.delete("/{id}")
async def delete_department(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).where(Department.id == id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.delete(dept)
    await db.commit()
    return {"detail": "Department deleted successfully"}
