"""业务对象候选数据（下拉框 / 搜索控件专用，登录即可访问）。

为什么要单独成一组接口
----------------------
前端下拉只需要「主键 + 编码 + 名称」，但管理页的列表接口返回的是**完整业务字段**：
商品带成本价、客户带联系方式与信用额度、供应商带账期、员工带手机邮箱。让下拉直接调
管理页接口就只有两条路：把 `xxx:view` 权限对所有人放开（等于把成本价和客户名单交给
所有账号），或者让没有该权限的角色一进页面就吃 403（"右侧有数据却提示权限不足"）。

于是这里提供一组只读候选接口：**只吐 id / 编码 / 名称，登录即可访问**；
管理页接口的权限模型（`customer:view` / `product:view` …）保持不变。

约定
----
* 候选实体与前端 `frontend/src/utils/catalogOptions.ts` 的 `ENTITY_CONFIGS` 一一对应；
* 返回全量候选（客户 1650 条这类量级也只有 id/编码/名称，约百 KB），不做分页——
  避免"短关键词把目标挤出一页"的老问题（历史上按 50 条截断导致搜不到目标客户）；
* 按名称排序，保证下拉顺序稳定。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import like_contains
from app.api.deps import CurrentUser
from app.core.database import get_db
from app.models.master import (
    Customer,
    Manufacturer,
    Product,
    ProductCategory,
    Supplier,
    Warehouse,
)
from app.models.org import Department, Employee
from app.schemas.options import OptionOut

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]

# 实体键 -> (模型, 编码字段, 名称字段)；编码字段为 None 表示该对象没有编码（厂家）
_SOURCES: dict[str, tuple[type, str | None, str]] = {
    "customer": (Customer, "code", "name"),
    "product": (Product, "sku", "name"),
    "category": (ProductCategory, "code", "name"),
    "manufacturer": (Manufacturer, None, "name"),
    "supplier": (Supplier, "code", "name"),
    "warehouse": (Warehouse, "code", "name"),
    "employee": (Employee, "code", "name"),
    "department": (Department, "code", "name"),
}


def _source(entity: str) -> tuple[type, str | None, str]:
    source = _SOURCES.get(entity)
    if source is None:
        raise HTTPException(
            status_code=404,
            detail=f"未知的对象类型：{entity}（可选 {'/'.join(_SOURCES)}）",
        )
    return source


def _columns(model: type, code_field: str | None):
    columns = [model.id.label("id"), getattr(model, "name").label("name")]
    if code_field:
        columns.append(getattr(model, code_field).label("code"))
    return columns


def _to_out(row) -> OptionOut:
    return OptionOut(id=row.id, name=row.name, code=getattr(row, "code", None))


@router.get("/{entity}", response_model=list[OptionOut], summary="业务对象候选（下拉 / 搜索）")
async def list_options(
    entity: str,
    db: Db,
    _: CurrentUser,
    keyword: Annotated[str | None, Query(description="按名称或编码模糊匹配，不传则返回全部")] = None,
):
    model, code_field, _name_field = _source(entity)
    stmt = select(*_columns(model, code_field))
    if keyword and keyword.strip():
        conditions = [like_contains(model.name, keyword)]
        if code_field:
            conditions.append(like_contains(getattr(model, code_field), keyword))
        stmt = stmt.where(or_(*conditions))
    rows = (await db.execute(stmt.order_by(model.name, model.id))).all()
    return [_to_out(row) for row in rows]


@router.get(
    "/{entity}/{item_id}",
    response_model=OptionOut,
    summary="按主键取候选（编辑态回填下拉显示文本）",
)
async def get_option(entity: str, item_id: int, db: Db, _: CurrentUser):
    model, code_field, _name_field = _source(entity)
    stmt = select(*_columns(model, code_field)).where(model.id == item_id)
    row = (await db.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="对象不存在")
    return _to_out(row)
