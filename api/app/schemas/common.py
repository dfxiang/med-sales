from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=200, description="每页条数")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class Message(BaseModel):
    message: str


class OKResponse(BaseModel):
    ok: bool = True


def page_of(items: list[T], total: int, page: int, size: int) -> Page[T]:
    return Page(items=items, total=total, page=page, size=size)
