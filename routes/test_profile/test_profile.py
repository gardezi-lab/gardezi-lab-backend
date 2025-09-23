from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_
from sqlalchemy.orm import joinedload, selectinload
from models.models import TestProfile
from schemas.schemas import TestProfileCreate, TestProfileResponse
from database.database import get_db

router = APIRouter(prefix="/test-profile", tags=["Test Profile"])


# ✅ Get all test profiles with filtering
@router.get("/", response_model=list[TestProfileResponse])
async def get_all_test_profiles(
    db: AsyncSession = Depends(get_db),
    department_id: Optional[int] = None,
    min_fee: Optional[int] = None,
    max_fee: Optional[int] = None,
    search: Optional[str] = None
):
    query = select(TestProfile).options(joinedload(TestProfile.department_rel))

    if department_id:
        query = query.where(TestProfile.department_id == department_id)
    if min_fee:
        query = query.where(TestProfile.fee >= min_fee)
    if max_fee:
        query = query.where(TestProfile.fee <= max_fee)
    if search:
        query = query.where(TestProfile.test_name.ilike(f"%{search}%"))

    result = await db.execute(query)
    return result.scalars().all()


# ✅ Searching route (test_name, report_name, test_code, short_code)
@router.get("/search/", response_model=list[TestProfileResponse])
async def search_test_profiles(
    name: str,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(TestProfile)
        .options(joinedload(TestProfile.department_rel))
        .where(
            or_(
                TestProfile.test_name.ilike(f"%{name}%"),
                TestProfile.report_name.ilike(f"%{name}%"),
                TestProfile.test_code.ilike(f"%{name}%"),
                TestProfile.short_code.ilike(f"%{name}%"),
            )
        )
    )
    result = await db.execute(query)
    return result.scalars().all()


# ✅ Get single test profile by ID
@router.get("/{id}", response_model=TestProfileResponse)
async def get_test_profile(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestProfile)
        .options(joinedload(TestProfile.department_rel))
        .where(TestProfile.id == id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test Profile not found")
    return test


# ✅ Create new test profile
@router.post("/", response_model=TestProfileResponse)
async def create_test_profile(
    request: TestProfileCreate,
    db: AsyncSession = Depends(get_db)
):
    new_test = TestProfile(**request.dict())
    db.add(new_test)
    await db.commit()
    await db.refresh(new_test)

    # ✅ eager load relation
    result = await db.execute(
        select(TestProfile)
        .options(selectinload(TestProfile.department_rel))
        .where(TestProfile.id == new_test.id)
    )
    return result.scalar_one_or_none()


# ✅ Update test profile
@router.put("/{id}", response_model=TestProfileResponse)
async def update_test_profile(id: int, request: TestProfileCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestProfile).where(TestProfile.id == id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test Profile not found")
    
    await db.execute(
        update(TestProfile)
        .where(TestProfile.id == id)
        .values(**request.dict())
    )
    await db.commit()

    updated = await db.execute(
        select(TestProfile)
        .options(joinedload(TestProfile.department_rel))
        .where(TestProfile.id == id)
    )
    return updated.scalar_one()


# ✅ Delete test profile
@router.delete("/{id}")
async def delete_test_profile(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestProfile).where(TestProfile.id == id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test Profile not found")
    await db.delete(test)
    await db.commit()
    return {"detail": "Test Profile deleted successfully"}
