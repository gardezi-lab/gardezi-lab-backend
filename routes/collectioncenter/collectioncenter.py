from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from models.models import CollectionCenter
from schemas.schemas import CollectionCenterCreate, CollectionCenterResponse
from database.database import get_db

router = APIRouter(prefix="/collectioncenter", tags=["CollectionCenter"])

# ✅ Create Collection Center
@router.post("/", response_model=CollectionCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_collection_center(request: CollectionCenterCreate, db: AsyncSession = Depends(get_db)):
    new_lab = CollectionCenter(**request.dict())
    db.add(new_lab)
    await db.commit()
    await db.refresh(new_lab)
    return new_lab

# ✅ Get all Labs (no search here)
@router.get("/", response_model=list[CollectionCenterResponse])
async def get_all_labs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CollectionCenter))
    return result.scalars().all()

# ✅ Search Labs by name (dedicated route)
@router.get("/search/", response_model=list[CollectionCenterResponse])
async def search_labs(name: str, db: AsyncSession = Depends(get_db)):
    query = select(CollectionCenter).where(CollectionCenter.lab_name.ilike(f"%{name}%"))
    result = await db.execute(query)
    labs = result.scalars().all()
    if not labs:
        raise HTTPException(status_code=404, detail="No labs found matching the search")
    return labs

# ✅ Get Lab by ID
@router.get("/{id}", response_model=CollectionCenterResponse)
async def get_lab(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CollectionCenter).where(CollectionCenter.id == id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    return lab

# ✅ Update Lab
@router.put("/{id}", response_model=CollectionCenterResponse)
async def update_lab(id: int, request: CollectionCenterCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CollectionCenter).where(CollectionCenter.id == id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    await db.execute(update(CollectionCenter).where(CollectionCenter.id == id).values(**request.dict()))
    await db.commit()
    updated = await db.execute(select(CollectionCenter).where(CollectionCenter.id == id))
    return updated.scalar_one()

# ✅ Delete Lab
@router.delete("/{id}")
async def delete_lab(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CollectionCenter).where(CollectionCenter.id == id))
    lab = result.scalar_one_or_none()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")
    await db.delete(lab)
    await db.commit()
    return {"detail": "Lab deleted successfully"}
