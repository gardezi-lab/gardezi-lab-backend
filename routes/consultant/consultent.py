from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_
from models.models import Consultant
from schemas.schemas import ConsultantCreate, ConsultantResponse
from database.database import get_db

router = APIRouter(prefix="/consultant", tags=["consultant"])

# ✅ Create
@router.post("/", response_model=ConsultantResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor_lab(request: ConsultantCreate, db: AsyncSession = Depends(get_db)):
    new_record = Consultant(**request.dict())
    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)
    return new_record

# ✅ Get all
@router.get("/", response_model=list[ConsultantResponse])
async def get_all_doctor_lab(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Consultant))
    return result.scalars().all()

# ✅ Get single by ID
@router.get("/{id}", response_model=ConsultantResponse)
async def get_doctor_lab(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Consultant).where(Consultant.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

# ✅ Update
@router.put("/{id}", response_model=ConsultantResponse)
async def update_doctor_lab(id: int, request: ConsultantCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Consultant).where(Consultant.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.execute(
        update(Consultant).where(Consultant.id == id).values(**request.dict())
    )
    await db.commit()

    updated = await db.execute(select(Consultant).where(Consultant.id == id))
    return updated.scalar_one()

# ✅ Delete
@router.delete("/{id}")
async def delete_doctor_lab(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Consultant).where(Consultant.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    await db.delete(record)
    await db.commit()
    return {"detail": "Record deleted successfully"}

# ✅ Search
@router.get("/search/", response_model=list[ConsultantResponse])
async def search_doctor_lab(
    q: str,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Consultant)
        .where(
            or_(
                Consultant.doctor_name.ilike(f"%{q}%"),
                Consultant.contact_no.ilike(f"%{q}%"),
                Consultant.hospital.ilike(f"%{q}%"),
                Consultant.username.ilike(f"%{q}%"),
                Consultant.age.ilike(f"%{q}%")
            )
        )
    )
    result = await db.execute(query)
    return result.scalars().all()
