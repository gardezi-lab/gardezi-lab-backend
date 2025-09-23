from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.database import get_db
from models.models import Company, Department
from auth.utils import pwd_context, DEFAULT_PASSWORD
from schemas.schemas import CompanyCreate, CompanyUpdate, CompanyResponse
from typing import List

router = APIRouter(prefix="/company", tags=["Company"])

# ---------------- Sync/Create Company ----------------
async def create_or_update_company(db: AsyncSession, company_data: CompanyCreate):
    # Check if company with same username exists
    result = await db.execute(select(Company).where(Company.username == company_data.username))
    existing = result.scalar_one_or_none()

    # Use default password if not provided
    password_to_hash = company_data.password or DEFAULT_PASSWORD
    hashed_password = pwd_context.hash(password_to_hash)

    if existing:
        # Update existing company
        existing.name = company_data.name
        existing.head_id = company_data.head_id
        existing.contact_no = company_data.contact_no
        existing.password = hashed_password
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Create new company
        new_company = Company(
            name=company_data.name,
            head_id=company_data.head_id,
            contact_no=company_data.contact_no,
            username=company_data.username,
            password=hashed_password
        )
        db.add(new_company)
        await db.commit()
        await db.refresh(new_company)
        return new_company
# ---------------- Helper ----------------
async def create_or_update_company(db: AsyncSession, company_data: CompanyCreate | CompanyUpdate):
    # validate head department
    if company_data.head_id:
        result = await db.execute(select(Department).where(Department.id == company_data.head_id))
        department = result.scalar_one_or_none()
        if not department:
            raise HTTPException(
                status_code=404,
                detail=f"Department with id {company_data.head_id} not found"
            )

    # check if company already exists by username
    result = await db.execute(select(Company).where(Company.username == company_data.username))
    db_company = result.scalar_one_or_none()

    if db_company:
        # update existing company
        if getattr(company_data, "name", None):
            db_company.name = company_data.name
        if getattr(company_data, "head_id", None) is not None:
            db_company.head_id = company_data.head_id
        if getattr(company_data, "contact_no", None):
            db_company.contact_no = company_data.contact_no
        if getattr(company_data, "password", None):
            db_company.password = Company.hash_password(company_data.password)
        db.add(db_company)
        await db.commit()
        await db.refresh(db_company)
        return db_company
    else:
        # create new company
        db_company = Company(
            name=company_data.name,
            head_id=company_data.head_id,
            contact_no=company_data.contact_no,
            username=company_data.username,
            password=Company.hash_password(company_data.password or DEFAULT_PASSWORD)
        )
        db.add(db_company)
        await db.commit()
        await db.refresh(db_company)
        return db_company
# ---------------- Create Company ----------------
@router.post("/", response_model=CompanyResponse)
async def create_company(company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    return await create_or_update_company(db, company)

# ---------------- Get All Companies ----------------
@router.get("/", response_model=List[CompanyResponse])
async def get_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company))
    companies = result.scalars().all()
    return companies

# ---------------- Get Single Company ----------------
@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

# ---------------- Update Company ----------------
@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(company_id: int, company: CompanyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.name is not None:
        existing.name = company.name
    if company.head_id is not None:
        existing.head_id = company.head_id
    if company.contact_no is not None:
        existing.contact_no = company.contact_no
    if company.username is not None:
        existing.username = company.username
    if company.password is not None:
        existing.password = pwd_context.hash(company.password)

    db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing

# ---------------- Delete Company ----------------
@router.delete("/{company_id}")
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    await db.delete(existing)
    await db.commit()
    return {"detail": "Company deleted successfully"}
