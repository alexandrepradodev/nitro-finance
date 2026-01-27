from uuid import UUID

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str


class CategoryUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool

    class Config:
        from_attributes = True