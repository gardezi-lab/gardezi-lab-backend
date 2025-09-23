from pydantic import BaseModel, EmailStr
from typing import Optional, List


# ---------------- Department ----------------
class DepartmentCreate(BaseModel):
    department: str

class DepartmentResponse(BaseModel):
    id: int
    department: str

    class Config:
        from_attributes = True


# ---------------- TestProfile ----------------
class TestProfileCreate(BaseModel):
    test_name: str
    report_name: Optional[str] = None
    test_code: Optional[str] = None
    short_code: Optional[str] = None
    sample_required: Optional[str] = None
    department_id: int   # sirf id input ke liye
    fee: Optional[int] = None
    delivery_time: Optional[int] = None
    serology_elisa: Optional[bool] = False
    interpretation: Optional[str] = None

class TestProfileResponse(BaseModel):
    id: int
    test_name: str
    report_name: Optional[str] = None
    test_code: Optional[str] = None
    short_code: Optional[str] = None
    sample_required: Optional[str] = None
    department_id: Optional[int] = None   # 🔧 fix here
    fee: Optional[int] = None
    delivery_time: Optional[int] = None
    serology_elisa: Optional[bool] = False
    interpretation: Optional[str] = None
    department_rel: Optional[DepartmentResponse] = None  

    class Config:
        from_attributes = True
# ---------------- TestParameter ----------------
class ParameterBase(BaseModel):
    name: str
    sub_heading: Optional[str] = None
    input_type: Optional[str] = None
    unit: Optional[str] = None
    normal_value: Optional[str] = None
    technique_details: Optional[str] = None
    default_value: Optional[str] = None

class ParameterCreate(ParameterBase):
    pass

class ParameterUpdate(BaseModel):
    name: Optional[str] = None
    sub_heading: Optional[str] = None
    input_type: Optional[str] = None
    unit: Optional[str] = None
    normal_value: Optional[str] = None
    technique_details: Optional[str] = None
    default_value: Optional[str] = None

class ParameterResponse(ParameterBase):
    id: int

    class Config:
        from_attributes = True


# ---------------- Consultant ----------------
class ConsultantCreate(BaseModel):
    doctor_name: str
    contact_no: str
    hospital: Optional[str] = None
    username: str
    age: Optional[float] = None

class ConsultantResponse(BaseModel):
    id: int
    doctor_name: str
    contact_no: str
    hospital: Optional[str] = None
    username: str
    age: Optional[float] = None

    class Config:
        from_attributes = True


# ---------------- CollectionCenter ----------------
class CollectionCenterCreate(BaseModel):
    lab_name: str
    head_name: str
    contact_no: str
    email: EmailStr
    login_password: str
    color_graphical: Optional[str] = None
    address: Optional[str] = None

class CollectionCenterResponse(BaseModel):
    id: int
    lab_name: str
    head_name: str
    contact_no: str
    email: EmailStr
    color_graphical: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------- Receptionist ----------------
class ReceptionistCreate(BaseModel):
    name: str
    username: str
    password: str
    color_graphical: Optional[str] = "#123456"
    collection_center_id: int

class ReceptionistResponse(BaseModel):
    id: int
    name: str
    username: str
    color_graphical: Optional[str]
    collection_center_id: int

    class Config:
        from_attributes = True


# ---------------- Technician ----------------
class TechnicianCreate(BaseModel):
    name: str
    username: str
    password: str
    color_graphical: Optional[str] = "#123456"
    collection_center_id: int

class TechnicianResponse(BaseModel):
    id: int
    name: str
    username: str
    color_graphical: Optional[str]
    collection_center_id: int

    class Config:
        from_attributes = True


# ---------------- Pathologist ----------------
class PathologistCreate(BaseModel):
    name: str
    description: Optional[str] = None
    username: str
    password: str
    color_graphical: Optional[str] = "#123456"
    department_ids: List[int]

class PathologistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    username: str
    color_graphical: Optional[str]
    departments: List[DepartmentResponse]

    class Config:
        from_attributes = True

# ---------------- Account Department User  ----------------
class AccountDepartmentUserCreate(BaseModel):
    name: str
    description: Optional[str] = None
    username: str
    password: str   # plain password (hash route me hoga)

class AccountDepartmentUserResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    username: str

    class Config:
        from_attributes = True
        
    
# ---------------- MAnager Account   ----------------
class ManagerAccountCreate(BaseModel):
    name: str
    about: Optional[str] = None
    username: str
    password: str   # plain password, hashing route me hoga

class ManagerAccountResponse(BaseModel):
    id: int
    name: str
    about: Optional[str]
    username: str

    class Config:
        from_attributes = True

# ---------------- Bank Account  ----------------
class BankAccountCreate(BaseModel):
    bank_name: str
    account_no: str
    branch: Optional[str] = None

class BankAccountResponse(BaseModel):
    id: int
    bank_name: str
    account_no: str
    branch: Optional[str]

    class Config:
        from_attributes = True
        
# ---------------- User Login  ----------------
        
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
#---------------- Company ----------------
class CompanyBase(BaseModel):
    name: str
    head_id: Optional[int] = None
    contact_no: Optional[str] = None
    username: str
    password: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    head_id: Optional[int] = None
    contact_no: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class CompanyResponse(BaseModel):
    id: int
    name: str
    head_id: Optional[int] = None
    contact_no: Optional[str] = None
    username: str

    class Config:
        from_attributes = True
        
#---------------- Pacakge ----------------        
class PackageBase(BaseModel):
    name: str
    price: float

class PackageCreate(PackageBase):
    pass

class Package(PackageBase):
    id: int

    class Config:
        orm_mode = True
    
#---------------- Test to Pacakge ----------------      

class TestToPackageBase(BaseModel):
    test_profile_id: int
    package_id: int

class TestToPackageCreate(TestToPackageBase):
    pass

class TestToPackageResponse(TestToPackageBase):
    id: int
    class Config:
        from_attributes= True

from models.models import PriorityEnum
class PatientEntryCreate(BaseModel):
    cell_no: str
    name: str
    father_or_husband_mr: Optional[str] = None
    age: Optional[int] = None

    # existing foreign keys
    company_id: Optional[int] = None
    referred_by_id: Optional[int] = None
    package_id: Optional[int] = None
    test_id: Optional[int] = None

    # 🔹 extra fields for name-based search
    company_name: Optional[str] = None
    referred_by_name: Optional[str] = None
    package_name: Optional[str] = None
    test_name: Optional[str] = None
    priority_name: Optional[str] = None

    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    sample: Optional[str] = None
    priority: PriorityEnum = PriorityEnum.normal
    remarks: Optional[str] = None

class PatientEntryResponse(PatientEntryCreate):
    id: int
    company_name: Optional[str] = None
    referred_by_name: Optional[str] = None
    package_name: Optional[str] = None
    test_name: Optional[str] = None

    class Config:
        from_attributes = True