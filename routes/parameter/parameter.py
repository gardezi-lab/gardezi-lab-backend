from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_
from models.models import Parameter
from schemas.schemas import ParameterCreate, ParameterResponse
from database.database import get_db

router = APIRouter(prefix="/test-parameter", tags=["Test Parameter"])


@router.post("/", response_model=ParameterResponse, status_code=status.HTTP_201_CREATED)
async def create_test_parameter(request: ParameterCreate, db: AsyncSession = Depends(get_db)):
    new_param = Parameter(**request.dict())
    db.add(new_param)
    await db.commit()
    await db.refresh(new_param)
    return new_param


@router.get("/", response_model=list[ParameterResponse])
async def get_all_test_parameters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parameter))
    return result.scalars().all()


# ✅ Searching route
@router.get("/search/", response_model=list[ParameterResponse])
async def search_test_parameters(
    q: str,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Parameter)
        .where(
            or_(
                Parameter.name.ilike(f"%{q}%"),
                Parameter.sub_heading.ilike(f"%{q}%"),
                Parameter.unit.ilike(f"%{q}%"),
                Parameter.normal_value.ilike(f"%{q}%")
            )
        )
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{id}", response_model=ParameterResponse)
async def get_test_parameter(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parameter).where(Parameter.id == id))
    param = result.scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Test Parameter not found")
    return param


@router.put("/{id}")
async def update_test_parameter(id: int, request: ParameterCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parameter).where(Parameter.id == id))
    param = result.scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Test Parameter not found")
    await db.execute(update(Parameter).where(Parameter.id == id).values(**request.dict()))
    await db.commit()
    return {"detail": "Test Parameter updated successfully"}


@router.delete("/{id}")
async def delete_test_parameter(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Parameter).where(Parameter.id == id))
    param = result.scalar_one_or_none()
    if not param:
        raise HTTPException(status_code=404, detail="Test Parameter not found")
    await db.delete(param)
    await db.commit()
    return {"detail": "Test Parameter deleted successfully"}
