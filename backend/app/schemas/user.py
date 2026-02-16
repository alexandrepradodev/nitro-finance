from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.LEADER
    phone: str | None = None
    department_ids: list[UUID] = []
    company_ids: list[UUID] = []


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: UserRole | None = None
    phone: str | None = None
    is_active: bool | None = None
    department_ids: list[UUID] | None = None
    company_ids: list[UUID] | None = None


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: UserRole
    phone: str | None
    is_active: bool

    class Config:
        from_attributes = True


class CompanyBasicResponse(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True


class UserWithDepartmentsResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: UserRole
    phone: str | None
    is_active: bool
    departments: list["DepartmentBasicResponse"] = []
    companies: list["CompanyBasicResponse"] = []

    class Config:
        from_attributes = True


class DepartmentBasicResponse(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True