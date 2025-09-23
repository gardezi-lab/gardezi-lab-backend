from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from models.models import Package
from schemas.schemas import PackageCreate, Package as PackageResponse
from database.database import get_db

router = APIRouter(prefix="/packages", tags=["Package"])


# ✅ Create Package
@router.post("/", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(request: PackageCreate, db: AsyncSession = Depends(get_db)):
    # Check if package with same name exists (optional)
    existing = await db.execute(select(Package).where(Package.name == request.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Package with this name already exists")

    new_package = Package(
        name=request.name,
        price=request.price
    )
    db.add(new_package)
    await db.commit()
    await db.refresh(new_package)
    return new_package


# ✅ Get All Packages
@router.get("/", response_model=List[PackageResponse])
async def get_packages(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).offset(skip).limit(limit))
    return result.scalars().all()


# ✅ Get Package by ID
@router.get("/{id}", response_model=PackageResponse)
async def get_package(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).where(Package.id == id))
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return package


# ✅ Update Package
@router.put("/{id}", response_model=PackageResponse)
async def update_package(id: int, request: PackageCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).where(Package.id == id))
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    package.name = request.name
    package.price = request.price

    await db.commit()
    await db.refresh(package)
    return package


# ✅ Delete Package
@router.delete("/{id}")
async def delete_package(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Package).where(Package.id == id))
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    await db.delete(package)
    await db.commit()
    return {"detail": "Package deleted successfully"}
