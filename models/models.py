from database.database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text,Enum, Float, Table
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
import enum


# ================= Many-to-Many (Pathologist <-> Department) =================
pathologist_department = Table(
    "pathologist_department",
    Base.metadata,
    Column("pathologist_id", Integer, ForeignKey("Pathologist.id"), primary_key=True),
    Column("department_id", Integer, ForeignKey("departments.id"), primary_key=True)
)


# ================= Department =================
class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String, unique=True, nullable=False)

    # Many-to-Many with Pathologist
    pathologists = relationship(
        "Pathologist",
        secondary=pathologist_department,
        back_populates="departments"
    )

    # One-to-Many with TestProfile
    test_profiles = relationship("TestProfile", back_populates="department_rel")
#===============TESTPROFILLE=================================
class TestProfile(Base):
    __tablename__ = "test_profiles"

    id = Column(Integer, primary_key=True, index=True)
    test_name = Column(String, nullable=False)
    report_name = Column(String, nullable=True)
    test_code = Column(String, unique=True, nullable=True)
    short_code = Column(String, nullable=True)
    sample_required = Column(String, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    fee = Column(Integer, nullable=True)
    delivery_time = Column(Integer, nullable=True)
    serology_elisa = Column(Boolean, default=False)
    interpretation = Column(String, nullable=True)

    # Relationship with Department
    department_rel = relationship("Department", back_populates="test_profiles")

    # ✅ Relationship with TestToPackage
    package_links = relationship("TestToPackage", back_populates="test_profile")

# ================= Parameter =================
class Parameter(Base):
    __tablename__ = "test_parameters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Parameter
    sub_heading = Column(String(255), nullable=True)  # Sub Heading
    input_type = Column(String(100), nullable=True)  # Input type
    unit = Column(String(100), nullable=True)  # Unit
    normal_value = Column(String(255), nullable=True)  # Normal Value
    technique_details = Column(Text, nullable=True)  # Technique details of Test
    default_value = Column(String(255), nullable=True)  # Default value


# ================= Consultant =================
class Consultant(Base):
    __tablename__ = "Consultant"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String, nullable=False)
    contact_no = Column(String, nullable=False)
    hospital = Column(String, nullable=True)
    username = Column(String, unique=True, nullable=False)
    age = Column(Float, nullable=True)


# ================= CollectionCenter =================
class CollectionCenter(Base):
    __tablename__ = "CollectionCenter"

    id = Column(Integer, primary_key=True, index=True)
    lab_name = Column(String, nullable=False)
    head_name = Column(String, nullable=False)
    contact_no = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    login_password = Column(String, nullable=False)  # store hashed password
    color_graphical = Column(String, nullable=True, default="#123456")
    address = Column(String, nullable=True)

    # Relationships (One-to-Many)
    receptionists = relationship("Receptionist", back_populates="collection_center")
    technicians = relationship("Technician", back_populates="collection_center")


# ================= Receptionist =================
class Receptionist(Base):
    __tablename__ = "Receptionist"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    color_graphical = Column(String, nullable=True)
    collection_center_id = Column(Integer, ForeignKey("CollectionCenter.id"))

    # Relationship back to CollectionCenter
    collection_center = relationship("CollectionCenter", back_populates="receptionists")


# ================= Technician =================
class Technician(Base):
    __tablename__ = "Technician"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    color_graphical = Column(String, nullable=True, default="#123456")
    collection_center_id = Column(Integer, ForeignKey("CollectionCenter.id"))

    # Relationship back to CollectionCenter
    collection_center = relationship("CollectionCenter", back_populates="technicians")


# ================= Pathologist =================
class Pathologist(Base):
    __tablename__ = "Pathologist"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # store hashed password
    color_graphical = Column(String, nullable=True, default="#123456")

    # Many-to-Many with Department
    departments = relationship(
        "Department",
        secondary=pathologist_department,
        back_populates="pathologists",
        lazy="selectin"
    )

# ================= Department Account User =================
class AccountDepartmentUser(Base):
    __tablename__ = "account_department_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)                # Account user name
    description = Column(Text, nullable=True)            # Description
    username = Column(String, unique=True, nullable=False)  # Username (unique)
    password = Column(String, nullable=False)            # Hashed password
    
# ================= Manager Account  =================
class ManagerAccount(Base):
    __tablename__ = "manager_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)       # Receptionist Name
    about = Column(Text, nullable=True)                      # About
    username = Column(String, unique=True, nullable=False)   # Username (unique)
    password = Column(String, nullable=False)                # Hashed Password
    
# ================= Bank Account  =================
class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String, nullable=False)        # Bank Name
    account_no = Column(String, unique=True, nullable=False)  # Account No (unique)
    branch = Column(String, nullable=True)            # Branch
    
    
# ================= User Login  =================    
class AuthUser(Base):
    __tablename__ = "auth_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # hashed password
    
    
# ================= Company  =================    
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = "changeme123"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    head_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # link to Department
    contact_no = Column(String, nullable=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    # Relationship with Department
    head = relationship("Department")

    @staticmethod
    def hash_password(password: str):
        return pwd_context.hash(password)
    
    
# ================= Package  =================
class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)

    # ✅ Relationship with TestToPackage
    test_mappings = relationship("TestToPackage", back_populates="package")





# ================= Test To Package  =================
class TestToPackage(Base):
    __tablename__ = "test_to_package"

    id = Column(Integer, primary_key=True, index=True)
    test_profile_id = Column(Integer, ForeignKey("test_profiles.id"), nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)

    # ✅ Relationships
    test_profile = relationship("TestProfile", back_populates="package_links")
    package = relationship("Package", back_populates="test_mappings")

# ================= Patient Entry  =================
# ✅ Priority Enum


class PriorityEnum(str, enum.Enum):
    normal = "normal"
    urgent = "urgent"
    




class PatientEntry(Base):
    __tablename__ = "patient_entry"

    id = Column(Integer, primary_key=True, index=True)
    cell_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    father_or_husband_mr = Column(String, nullable=True)
    age = Column(Integer, nullable=True)

    # Foreign Keys
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    referred_by_id = Column(Integer, ForeignKey("Consultant.id"), nullable=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)
    test_id = Column(Integer, ForeignKey("test_profiles.id"), nullable=True)

    gender = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    sample = Column(String, nullable=True)
    priority = Column(Enum(PriorityEnum), default=PriorityEnum.normal)
    remarks = Column(Text, nullable=True)

    # Relationships
    company = relationship("Company")
    consultant = relationship("Consultant")
    package = relationship("Package")
    test = relationship("TestProfile")




