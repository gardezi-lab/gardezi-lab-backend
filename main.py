

from fastapi import FastAPI
from database.database import engine,SessionLocal
from models.models import Base
from routes.test_profile import test_profile
from routes.department import department
from routes.parameter import parameter
from routes.consultant import consultent
from routes.collectioncenter import collectioncenter
from routes.receptionist import receptionist
from routes.technician import technician
from routes.pathologist import pathologist
from routes.account_department_user import account_department_user
from routes.manager_accounts import manager_accounts
from routes.bank_accounts import bank_accounts
from routes.auth import auth
from sqlalchemy.ext.asyncio import AsyncSession
from routes.auth.auth import router as auth_router, sync_users
from routes.company import company
from routes.package import package
from routes.test_to_package import test_to_package
from routes.patient_entry import patient_entry

# from routes.auth import sync_users

# ---------------- Swagger Tags Metadata ---------------- #
tags_metadata = [
    {"name": "Department", "description": "CRUD for Department"},
    {"name": "Test Profile", "description": "CRUD for Test Profile"},
    {"name": "Parameter", "description": "CRUD for Test Parameter"},
   
]

app = FastAPI(
    title="Gardezi API",
    description="APIs for managing Department, Test Profiles, Parameters and Consultants ",
    version="1.0.0",
    openapi_tags=tags_metadata
)

# Create tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


    async with SessionLocal() as session:
        await sync_users(session)
        
# Routers include
app.include_router(department.router)
app.include_router(test_profile.router)
app.include_router(parameter.router)
app.include_router(consultent.router)
app.include_router(collectioncenter.router)
app.include_router(receptionist.router)
app.include_router(technician.router)
app.include_router(pathologist.router)
app.include_router(account_department_user.router)
app.include_router(manager_accounts.router)
app.include_router(bank_accounts.router)
app.include_router(auth.router)
app.include_router(company.router)
app.include_router(package.router)
app.include_router(test_to_package.router)
app.include_router(patient_entry.router)


# # main.py
# import asyncio
# from fastapi import FastAPI, Depends, status, HTTPException
# import schemas.schemas, models.models
# from database.database import engine, SessionLocal
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select

# # ---------------- Swagger Tags Metadata ---------------- #
# tags_metadata = [
#     {
#         "name": "Department",
#         "description": "APIs related to Department management (CRUD operations).",
#     },
#     {
#         "name": "Test Profile",
#         "description": "APIs related to Test & Profile management (CRUD operations).",
#     },
#     {
#         "name": "Parameter ",
#         "description": "APIs related to Parameter  (CRUD operations).",
#     },
# ]

# app = FastAPI(
#     title="Department & Test Profile API",
#     description="This project contains APIs for managing **Departments** and **Test Profiles** in the lab system.",
#     version="1.0.0",
#     openapi_tags=tags_metadata,
# )


# # ✅ Create tables asynchronously
# async def init_models():
#     async with engine.begin() as conn:
#         await conn.run_sync(models.models.Base.metadata.create_all)


# @app.on_event("startup")
# async def on_startup():
#     await init_models()


# # ✅ Dependency - Async DB session
# async def get_db() -> AsyncSession:
#     async with SessionLocal() as session:
#         yield session


# @app.get("/", tags=["Department", "Test Profile"])
# async def root():
#     return {"message": "Department & TestProfile API is running"}


# # ---------------- DEPARTMENT ROUTES ---------------- #

# @app.post("/department", status_code=status.HTTP_201_CREATED,
#           response_model=schemas.schemas.DepartmentResponse, tags=["Department"])
# async def create_department(request: schemas.schemas.DepartmentCreate, db: AsyncSession = Depends(get_db)):
#     new_department = models.models.Department(department=request.department)
#     db.add(new_department)
#     await db.commit()
#     await db.refresh(new_department)
#     return new_department


# @app.get("/department", response_model=list[schemas.schemas.DepartmentResponse], tags=["Department"])
# async def get_all_departments(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(models.models.Department))
#     departments = result.scalars().all()
#     return departments

# @app.get("/department/search", response_model=list[schemas.schemas.DepartmentResponse], tags=["Department"])
# async def search_department(name: str, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         select(models.models.Department).where(
#             models.models.Department.department.ilike(f"%{name}%")
#         )
#     )
#     departments = result.scalars().all()
#     return departments

# @app.get("/department/{id}", response_model=schemas.schemas.DepartmentResponse, tags=["Department"])
# async def get_department_by_id(id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         select(models.models.Department).where(models.models.Department.id == id)
#     )
#     department = result.scalar_one_or_none()
#     if not department:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Department with id {id} not found"
#         )
#     return department

# @app.put("/department/{id}", status_code=status.HTTP_202_ACCEPTED, tags=["Department"])
# async def update_department(id: int, request: schemas.schemas.DepartmentCreate, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         models.models.Department.__table__.select().where(models.models.Department.id == id)
#     )
#     department = result.scalar_one_or_none()
#     if not department:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department with id {id} not found")

#     await db.execute(
#         models.models.Department.__table__.update().where(models.models.Department.id == id).values(**request.dict())
#     )
#     await db.commit()
#     return {"detail": "Department updated successfully"}


# @app.delete("/department/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Department"])
# async def delete_department(id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         models.models.Department.__table__.select().where(models.models.Department.id == id)
#     )
#     department = result.scalar_one_or_none()
#     if not department:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Department with id {id} not found")

#     await db.execute(
#         models.models.Department.__table__.delete().where(models.models.Department.id == id)
#     )
#     await db.commit()
#     return {"detail": "Department deleted successfully"}


# # ---------------- TEST & PROFILE ROUTES ---------------- #

# @app.post("/test-profile", status_code=status.HTTP_201_CREATED,
#           response_model=schemas.schemas.TestProfileResponse, tags=["Test Profile"])
# async def create_test_profile(request: schemas.schemas.TestProfileCreate, db: AsyncSession = Depends(get_db)):
#     new_test = models.models.TestProfile(**request.dict())
#     db.add(new_test)
#     await db.commit()
#     await db.refresh(new_test)
#     return new_test


# @app.get("/test-profile", response_model=list[schemas.schemas.TestProfileResponse], tags=["Test Profile"])
# async def get_all_test_profiles(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(models.models.TestProfile))
#     return result.scalars().all()


# @app.get("/test-profile/search", response_model=list[schemas.schemas.TestProfileResponse], tags=["Test Profile"])
# async def search_test_profile(name: str, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         select(models.models.TestProfile).where(
#             models.models.TestProfile.test_name.ilike(f"%{name}%")
#         )
#     )
#     tests = result.scalars().all()
#     if not tests:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No test profiles found with name containing '{name}'"
#         )
#     return tests


# @app.get("/test-profile/{id}", response_model=schemas.schemas.TestProfileResponse, tags=["Test Profile"])
# async def get_test_profile_by_id(id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         models.models.TestProfile.__table__.select().where(models.models.TestProfile.id == id)
#     )
#     test = result.scalar_one_or_none()
#     if not test:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestProfile with id {id} not found")
#     return test


# @app.put("/test-profile/{id}", status_code=status.HTTP_202_ACCEPTED, tags=["Test Profile"])
# async def update_test_profile(id: int, request: schemas.schemas.TestProfileCreate, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         select(models.models.TestProfile).where(models.models.TestProfile.id == id)
#     )
#     test = result.scalar_one_or_none()
#     if not test:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestProfile with id {id} not found")

#     await db.execute(
#         update(models.models.TestProfile).where(models.models.TestProfile.id == id).values(**request.dict())
#     )
#     await db.commit()
#     return {"detail": "TestProfile updated successfully"}



# @app.delete("/test-profile/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Test Profile"])
# async def delete_test_profile(id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         models.models.TestProfile.__table__.select().where(models.models.TestProfile.id == id)
#     )
#     test = result.scalar_one_or_none()
#     if not test:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestProfile with id {id} not found")

#     await db.execute(
#         models.models.TestProfile.__table__.delete().where(models.models.TestProfile.id == id)
#     )
#     await db.commit()
#     return {"detail": "TestProfile deleted successfully"}

# # ---------------- TEST PARAMETER ROUTES ---------------- #

# @app.post("/test-parameter", status_code=status.HTTP_201_CREATED,
#           response_model=schemas.schemas.TestParameterResponse, tags=["Test Parameter"])
# async def create_test_parameter(request: schemas.schemas.TestParameterCreate, db: AsyncSession = Depends(get_db)):
#     new_param = models.models.TestParameter(**request.dict())
#     db.add(new_param)
#     await db.commit()
#     await db.refresh(new_param)
#     return new_param


# @app.get("/test-parameter", response_model=list[schemas.schemas.TestParameterResponse], tags=["Test Parameter"])
# async def get_all_test_parameters(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(models.models.TestParameter))
#     return result.scalars().all()


# @app.get("/test-parameter/search", response_model=list[schemas.schemas.TestParameterResponse], tags=["Test Parameter"])
# async def search_test_parameter(name: str, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         select(models.models.TestParameter).where(
#             models.models.TestParameter.name.ilike(f"%{name}%")
#         )
#     )
#     params = result.scalars().all()
#     if not params:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No test parameters found with name containing '{name}'"
#         )
#     return params


# @app.get("/test-parameter/{id}", response_model=schemas.schemas.TestParameterResponse, tags=["Test Parameter"])
# async def get_test_parameter_by_id(id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         models.models.TestParameter.__table__.select().where(models.models.TestParameter.id == id)
#     )
#     param = result.scalar_one_or_none()
#     if not param:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestParameter with id {id} not found")
#     return param


# @app.put("/test-parameter/{id}", status_code=status.HTTP_202_ACCEPTED, tags=["Test Parameter"])
# async def update_test_parameter(id: int, request: schemas.schemas.TestParameterCreate, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         select(models.models.TestParameter).where(models.models.TestParameter.id == id)
#     )
#     param = result.scalar_one_or_none()
#     if not param:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestParameter with id {id} not found")

#     await db.execute(
#         update(models.models.TestParameter).where(models.models.TestParameter.id == id).values(**request.dict())
#     )
#     await db.commit()
#     return {"detail": "TestParameter updated successfully"}


# @app.delete("/test-parameter/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Test Parameter"])
# async def delete_test_parameter(id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         models.models.TestParameter.__table__.select().where(models.models.TestParameter.id == id)
#     )
#     param = result.scalar_one_or_none()
#     if not param:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TestParameter with id {id} not found")

#     await db.execute(
#         models.models.TestParameter.__table__.delete().where(models.models.TestParameter.id == id)
#     )
#     await db.commit()
#     return {"detail": "TestParameter deleted successfully"}


        
# import os
# import ssl
# from dotenv import load_dotenv
# from fastapi import FastAPI, Depends
# from pydantic import BaseModel
# from sqlalchemy import Column, Integer, String
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker, declarative_base

# # Load environment variables
# load_dotenv()
# DATABASE_URL = os.getenv("DATABASE_URL")

# # SQLAlchemy async URL (postgresql+asyncpg)
# if DATABASE_URL.startswith("postgresql://"):
#     DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# # SSL context for Neon
# ssl_context = ssl.create_default_context()

# # Async engine
# engine = create_async_engine(
#     DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1),
#     echo=True,
#     connect_args={"ssl": ssl_context}
# )
# SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
# Base = declarative_base()

# # DB Model
# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String(50), nullable=False)
#     age = Column(Integer, nullable=False)

# # Pydantic schema
# class UserCreate(BaseModel):
#     username: str
#     age: int

# # FastAPI app
# app = FastAPI()

# # Dependency
# async def get_session():
#     async with SessionLocal() as session:
#         yield session

# # Root endpoint
# @app.get("/")
# def read_root():
#     return {"message": "Hello World from FastAPI 🚀"}

# # POST endpoint
# @app.post("/users")
# async def create_user(user: UserCreate, session: AsyncSession = Depends(get_session)):
#     new_user = User(username=user.username, age=user.age)
#     session.add(new_user)
#     await session.commit()
#     await session.refresh(new_user)
#     return {"id": new_user.id, "username": new_user.username, "age": new_user.age}

# # Auto-create tables on startup (for dev/demo)
# @app.on_event("startup")
# async def on_startup():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)


