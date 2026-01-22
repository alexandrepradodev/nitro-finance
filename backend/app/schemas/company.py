from uuid import UUID

from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str


class CompanyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool

    class Config:
        from_attributes = True