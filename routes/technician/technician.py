from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from models.models import Technician
from schemas.schemas import TechnicianCreate, TechnicianResponse
from database.database import get_db
from passlib.context import CryptContext

router = APIRouter(prefix="/technician", tags=["Technician"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# ✅ Create Technician
@router.post("/", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED)
async def create_technician(request: TechnicianCreate, db: AsyncSession = Depends(get_db)):
    # check username uniqueness
    result = await db.execute(select(Technician).where(Technician.username == request.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_tech = Technician(
        name=request.name,
        username=request.username,
        password=hash_password(request.password),
        color_graphical=request.color_graphical,
        collection_center_id=request.collection_center_id
    )
    db.add(new_tech)
    await db.commit()
    await db.refresh(new_tech)
    return new_tech

# ✅ Get all Technicians
@router.get("/", response_model=List[TechnicianResponse])
async def get_all_technicians(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Technician))
    return result.scalars().all()

# ✅ Get Technician by ID
@router.get("/{id}", response_model=TechnicianResponse)
async def get_technician(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Technician).where(Technician.id == id))
    tech = result.scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech

# ✅ Update Technician
@router.put("/{id}", response_model=TechnicianResponse)
async def update_technician(id: int, request: TechnicianCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Technician).where(Technician.id == id))
    tech = result.scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # update fields
    update_data = request.dict()
    update_data["password"] = hash_password(request.password)
    await db.execute(update(Technician).where(Technician.id == id).values(**update_data))
    await db.commit()

    updated = await db.execute(select(Technician).where(Technician.id == id))
    return updated.scalar_one()

# ✅ Delete Technician
@router.delete("/{id}")
async def delete_technician(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Technician).where(Technician.id == id))
    tech = result.scalar_one_or_none()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    await db.delete(tech)
    await db.commit()
    return {"detail": "Technician deleted successfully"}
