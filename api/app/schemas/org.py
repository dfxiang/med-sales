from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None


class DepartmentUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    created_at: datetime


class EmployeeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    department_id: int
    position: str | None = None
    manager_id: int | None = None
    hire_date: date
    employment_status: str = "在职"


class EmployeeUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    department_id: int | None = None
    position: str | None = None
    manager_id: int | None = None
    hire_date: date | None = None
    employment_status: str | None = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    gender: str | None
    phone: str | None
    email: str | None
    department_id: int
    position: str | None
    manager_id: int | None
    hire_date: date
    employment_status: str
    created_at: datetime
