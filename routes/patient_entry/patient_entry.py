from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_
from database.database import get_db
from models.models import PatientEntry, Company, Consultant, Package, TestProfile
from schemas.schemas import PatientEntryCreate, PatientEntryResponse
from models.models import PriorityEnum


router = APIRouter(prefix="/patient-Entry", tags=["Patient Entry"])


# ✅ Create
@router.post("/", response_model=PatientEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_order(request: PatientEntryCreate, db: AsyncSession = Depends(get_db)):

    # ✅ resolve company name to id
    company_id = request.company_id
    if not company_id and request.company_name:
        result = await db.execute(select(Company).where(Company.name.ilike(request.company_name)))
        company = result.scalar_one_or_none()
        if company:
            company_id = company.id

    # ✅ resolve consultant name to id
    referred_by_id = request.referred_by_id
    if not referred_by_id and request.referred_by_name:
        result = await db.execute(select(Consultant).where(Consultant.doctor_name.ilike(request.referred_by_name)))
        consultant = result.scalar_one_or_none()
        if consultant:
            referred_by_id = consultant.id

    # ✅ resolve test name to id
    test_id = request.test_id
    if not test_id and request.test_name:
        result = await db.execute(select(TestProfile).where(TestProfile.test_name.ilike(request.test_name)))
        test = result.scalar_one_or_none()
        if test:
            test_id = test.id

    # ✅ resolve package name to id
    package_id = request.package_id
    if not package_id and request.package_name:
        result = await db.execute(select(Package).where(Package.name.ilike(request.package_name)))
        package = result.scalar_one_or_none()
        if package:
            package_id = package.id

    # ✅ resolve priority name (agar enum me diya gaya ho to)
    priority = request.priority
    if request.priority_name:
        try:
            priority = PriorityEnum[request.priority_name.lower()]
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid priority name")

    # ✅ ab record banado
    new_record = PatientEntry(
        cell_no=request.cell_no,
        name=request.name,
        father_or_husband_mr=request.father_or_husband_mr,
        age=request.age,
        company_id=company_id,
        referred_by_id=referred_by_id,
        package_id=package_id,
        test_id=test_id,
        gender=request.gender,
        email=request.email,
        address=request.address,
        sample=request.sample or request.sample_name,  # agar sample_name diya ho
        priority=priority,
        remarks=request.remarks,
    )

    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)
    return await build_response(new_record, db)


# ✅ Get all
@router.get("/", response_model=List[PatientEntryResponse])
async def get_all_patient_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientEntry))
    records = result.scalars().all()
    return [await build_response(r, db) for r in records]


# ✅ Get single
@router.get("/{id}", response_model=PatientEntryResponse)
async def get_patient_order(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientEntry).where(PatientEntry.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Patient order not found")
    return await build_response(record, db)


# ✅ Update
@router.put("/{id}", response_model=PatientEntryResponse)
async def update_patient_order(id: int, request: PatientEntryCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientEntry).where(PatientEntry.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Patient order not found")

    await db.execute(
        update(PatientEntry).where(PatientEntry.id == id).values(**request.dict())
    )
    await db.commit()

    updated = await db.execute(select(PatientEntry).where(PatientEntry.id == id))
    return await build_response(updated.scalar_one(), db)


# ✅ Delete
@router.delete("/{id}")
async def delete_patient_order(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PatientEntry).where(PatientEntry.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Patient order not found")

    await db.delete(record)
    await db.commit()
    return {"detail": "Patient order deleted successfully"}


# ✅ Search
@router.get("/search/", response_model=List[PatientEntryResponse])
async def search_patient_orders(q: str, db: AsyncSession = Depends(get_db)):
    query = (
        select(PatientEntry)
        .where(
            or_(
                PatientEntry.name.ilike(f"%{q}%"),          # patient name
                PatientEntry.cell_no.ilike(f"%{q}%"),          # phone
                PatientEntry.address.ilike(f"%{q}%"),       # address
                PatientEntry.remarks.ilike(f"%{q}%"),       # remarks
            )
        )
    )
    result = await db.execute(query)
    records = result.scalars().all()
    return [await build_response(r, db) for r in records]


# ✅ Helper function to enrich response
async def build_response(record: PatientEntry, db: AsyncSession) -> PatientEntryResponse:
    response = PatientEntryResponse.from_orm(record)

    if record.company_id:
        company = await db.get(Company, record.company_id)
        response.company_name = company.name if company else None

    if record.referred_by_id:
        consultant = await db.get(Consultant, record.referred_by_id)
        response.referred_by_name = consultant.doctor_name if consultant else None

    if record.package_id:
        package = await db.get(Package, record.package_id)
        response.package_name = package.name if package else None

    if record.test_id:
        test = await db.get(TestProfile, record.test_id)
        response.test_name = test.test_name if test else None

    return response
