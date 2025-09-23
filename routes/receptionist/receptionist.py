# routes/receptionist.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from passlib.context import CryptContext
from typing import List
from models.models import Receptionist, CollectionCenter
from schemas.schemas import ReceptionistCreate, ReceptionistResponse
from database.database import get_db

router = APIRouter(prefix="/receptionist", tags=["Receptionist"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

# Create Receptionist
@router.post("/", response_model=ReceptionistResponse, status_code=201)
async def create_receptionist(request: ReceptionistCreate, db: AsyncSession = Depends(get_db)):
    # 1️⃣ Check if username already exists
    result = await db.execute(select(Receptionist).where(Receptionist.username == request.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # 2️⃣ Hash the password
    hashed_password = hash_password(request.password)

    # 3️⃣ Create new Receptionist
    new_receptionist = Receptionist(
        name=request.name,
        username=request.username,
        password=hashed_password,
        color_graphical=request.color_graphical,
        collection_center_id=request.collection_center_id
    )

    # 4️⃣ Add to DB
    db.add(new_receptionist)
    await db.commit()
    await db.refresh(new_receptionist)

    return new_receptionist


# Get all Receptionists
@router.get("/", response_model=List[ReceptionistResponse])
async def get_all_receptionists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Receptionist))
    return result.scalars().all()

# Get single Receptionist by ID
@router.get("/{id}", response_model=ReceptionistResponse)
async def get_receptionist(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Receptionist).where(Receptionist.id == id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Receptionist not found")
    return rec

# Update Receptionist
@router.put("/{id}", response_model=ReceptionistResponse)
async def update_receptionist(id: int, request: ReceptionistCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Receptionist).where(Receptionist.id == id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Receptionist not found")

    # Check if CC exists
    cc_result = await db.execute(select(CollectionCenter).where(CollectionCenter.id == request.collection_center_id))
    cc = cc_result.scalar_one_or_none()
    if not cc:
        raise HTTPException(status_code=404, detail="Collection Center not found")

    await db.execute(
        update(Receptionist)
        .where(Receptionist.id == id)
        .values(
            name=request.name,
            username=request.username,
            password=hash_password(request.password),
            color_graphical=request.color_graphical,
            collection_center_id=request.collection_center_id
        )
    )
    await db.commit()

    updated = await db.execute(select(Receptionist).where(Receptionist.id == id))
    return updated.scalar_one()

# Delete Receptionist
@router.delete("/{id}")
async def delete_receptionist(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Receptionist).where(Receptionist.id == id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Receptionist not found")
    await db.delete(rec)
    await db.commit()
    return {"detail": "Receptionist deleted successfully"}
