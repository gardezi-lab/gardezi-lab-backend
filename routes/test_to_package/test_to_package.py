from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_
from models.models import TestToPackage, TestProfile, Package
from schemas.schemas import TestToPackageCreate, TestToPackageResponse
from database.database import get_db

router = APIRouter(prefix="/test-to-package", tags=["Test To Package"])

# ✅ Create (Add Test to Package)
@router.post("/", response_model=TestToPackageResponse, status_code=status.HTTP_201_CREATED)
async def create_test_to_package(request: TestToPackageCreate, db: AsyncSession = Depends(get_db)):
    # Check package exists
    pkg = await db.execute(select(Package).where(Package.id == request.package_id))
    if not pkg.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Package not found")

    # Check test exists
    test = await db.execute(select(TestProfile).where(TestProfile.id == request.test_profile_id))
    if not test.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="TestProfile not found")

    # Check duplicate
    exists = await db.execute(
        select(TestToPackage).where(
            TestToPackage.package_id == request.package_id,
            TestToPackage.test_profile_id == request.test_profile_id
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Test already added to package")

    new_record = TestToPackage(**request.dict())
    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)
    return new_record

# ✅ Get all
@router.get("/", response_model=List[TestToPackageResponse])
async def get_all_test_to_package(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestToPackage))
    return result.scalars().all()

# ✅ Get by ID
@router.get("/{id}", response_model=TestToPackageResponse)
async def get_test_to_package(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestToPackage).where(TestToPackage.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

# ✅ Update (change test or package mapping)
@router.put("/{id}", response_model=TestToPackageResponse)
async def update_test_to_package(id: int, request: TestToPackageCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestToPackage).where(TestToPackage.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    await db.execute(
        update(TestToPackage).where(TestToPackage.id == id).values(**request.dict())
    )
    await db.commit()

    updated = await db.execute(select(TestToPackage).where(TestToPackage.id == id))
    return updated.scalar_one()

# ✅ Delete
@router.delete("/{id}")
async def delete_test_to_package(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestToPackage).where(TestToPackage.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    await db.delete(record)
    await db.commit()
    return {"detail": "Record deleted successfully"}

# ✅ Search (by package name or test name)
@router.get("/search/", response_model=List[TestToPackageResponse])
async def search_test_to_package(q: str, db: AsyncSession = Depends(get_db)):
    query = (
        select(TestToPackage)
        .join(Package, TestToPackage.package_id == Package.id)
        .join(TestProfile, TestToPackage.test_profile_id == TestProfile.id)
        .where(
            or_(
                Package.name.ilike(f"%{q}%"),
                TestProfile.test_name.ilike(f"%{q}%")
            )
        )
    )
    result = await db.execute(query)
    return result.scalars().all()
