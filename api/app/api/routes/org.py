from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.org import Department, Employee
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.org import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)


# ----------------------------- 部门 -----------------------------
@router.get("/departments", response_model=Page[DepartmentOut], summary="部门列表")
async def list_departments(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
):
    stmt = select(Department).order_by(Department.id)
    if keyword:
        stmt = stmt.where(
            Department.name.ilike(f"%{keyword}%") | Department.code.ilike(f"%{keyword}%")
        )
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/departments/{department_id}", response_model=DepartmentOut, summary="部门详情")
async def get_department(department_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Department, department_id, "部门不存在")


@router.post("/departments", response_model=DepartmentOut, status_code=201, summary="创建部门")
async def create_department(payload: DepartmentCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Department).where(Department.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="部门编码已存在")
    return await create_and_commit(db, Department(**payload.model_dump()))


@router.put("/departments/{department_id}", response_model=DepartmentOut, summary="更新部门")
async def update_department(department_id: int, payload: DepartmentUpdate, db: Db, _: CurrentUser):
    department = await get_or_404(db, Department, department_id, "部门不存在")
    return await update_and_commit(db, department, payload.model_dump(exclude_unset=True))


@router.delete("/departments/{department_id}", response_model=Message, summary="删除部门")
async def delete_department(department_id: int, db: Db, _: CurrentUser):
    department = await get_or_404(db, Department, department_id, "部门不存在")
    await delete_and_commit(db, department)
    return Message(message="部门已删除")


# ----------------------------- 员工 -----------------------------
@router.get("/employees", response_model=Page[EmployeeOut], summary="员工列表")
async def list_employees(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    department_id: int | None = None,
    keyword: str | None = None,
    employment_status: str | None = None,
):
    stmt = select(Employee).order_by(Employee.id)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if employment_status:
        stmt = stmt.where(Employee.employment_status == employment_status)
    if keyword:
        stmt = stmt.where(
            Employee.name.ilike(f"%{keyword}%") | Employee.code.ilike(f"%{keyword}%")
        )
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/employees/{employee_id}", response_model=EmployeeOut, summary="员工详情")
async def get_employee(employee_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Employee, employee_id, "员工不存在")


@router.post("/employees", response_model=EmployeeOut, status_code=201, summary="创建员工")
async def create_employee(payload: EmployeeCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Employee).where(Employee.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="工号已存在")
    await get_or_404(db, Department, payload.department_id, "部门不存在")
    return await create_and_commit(db, Employee(**payload.model_dump()))


@router.put("/employees/{employee_id}", response_model=EmployeeOut, summary="更新员工")
async def update_employee(employee_id: int, payload: EmployeeUpdate, db: Db, _: CurrentUser):
    employee = await get_or_404(db, Employee, employee_id, "员工不存在")
    return await update_and_commit(db, employee, payload.model_dump(exclude_unset=True))


@router.delete("/employees/{employee_id}", response_model=Message, summary="删除员工")
async def delete_employee(employee_id: int, db: Db, _: CurrentUser):
    employee = await get_or_404(db, Employee, employee_id, "员工不存在")
    await delete_and_commit(db, employee)
    return Message(message="员工已删除")
