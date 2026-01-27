from uuid import UUID

from pydantic import BaseModel

from app.schemas.company import CompanyResponse


class DepartmentCreate(BaseModel):
    name: str
    company_id: UUID


class DepartmentUpdate(BaseModel):
    name: str | None = None
    company_id: UUID | None = None
    is_active: bool | None = None


class DepartmentResponse(BaseModel):
    id: UUID
    name: str
    company_id: UUID
    is_active: bool

    class Config:
        from_attributes = True


class DepartmentWithCompanyResponse(BaseModel):
    id: UUID
    name: str
    company_id: UUID
    is_active: bool
    company: CompanyResponse

    class Config:
        from_attributes = True