from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.core.database import get_db
from app.models.master import (
    Manufacturer,
    PriceHistory,
    Product,
    ProductCategory,
)
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.master import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ManufacturerCreate,
    ManufacturerOut,
    ManufacturerUpdate,
    PriceAdjustCreate,
    PriceHistoryOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
PERM_VIEW = Depends(require_permission("product:view"))
PERM_MANAGE = Depends(require_permission("product:manage"))


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)


# ----------------------------- 商品分类 -----------------------------
@router.get("/categories", response_model=Page[CategoryOut], summary="商品分类列表", dependencies=[PERM_VIEW])
async def list_categories(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
):
    stmt = select(ProductCategory).order_by(ProductCategory.sort_order, ProductCategory.id)
    if keyword:
        stmt = stmt.where(
            ProductCategory.name.ilike(f"%{keyword}%")
            | ProductCategory.code.ilike(f"%{keyword}%")
        )
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/categories/{category_id}", response_model=CategoryOut, summary="商品分类详情", dependencies=[PERM_VIEW])
async def get_category(category_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, ProductCategory, category_id, "分类不存在")


@router.post("/categories", response_model=CategoryOut, status_code=201, summary="创建商品分类", dependencies=[PERM_MANAGE])
async def create_category(payload: CategoryCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(ProductCategory).where(ProductCategory.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="分类编码已存在")
    return await create_and_commit(db, ProductCategory(**payload.model_dump()))


@router.put("/categories/{category_id}", response_model=CategoryOut, summary="更新商品分类", dependencies=[PERM_MANAGE])
async def update_category(category_id: int, payload: CategoryUpdate, db: Db, _: CurrentUser):
    category = await get_or_404(db, ProductCategory, category_id, "分类不存在")
    return await update_and_commit(db, category, payload.model_dump(exclude_unset=True))


@router.delete("/categories/{category_id}", response_model=Message, summary="删除商品分类", dependencies=[PERM_MANAGE])
async def delete_category(category_id: int, db: Db, _: CurrentUser):
    category = await get_or_404(db, ProductCategory, category_id, "分类不存在")
    await delete_and_commit(db, category)
    return Message(message="分类已删除")


# ----------------------------- 生产厂家 -----------------------------
@router.get("/manufacturers", response_model=Page[ManufacturerOut], summary="生产厂家列表", dependencies=[PERM_VIEW])
async def list_manufacturers(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
):
    stmt = select(Manufacturer).order_by(Manufacturer.id)
    if keyword:
        stmt = stmt.where(Manufacturer.name.ilike(f"%{keyword}%"))
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/manufacturers/{manufacturer_id}", response_model=ManufacturerOut, summary="厂家详情", dependencies=[PERM_VIEW])
async def get_manufacturer(manufacturer_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Manufacturer, manufacturer_id, "厂家不存在")


@router.post("/manufacturers", response_model=ManufacturerOut, status_code=201, summary="创建厂家", dependencies=[PERM_MANAGE])
async def create_manufacturer(payload: ManufacturerCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Manufacturer).where(Manufacturer.name == payload.name))
    if exists:
        raise HTTPException(status_code=400, detail="厂家已存在")
    return await create_and_commit(db, Manufacturer(**payload.model_dump()))


@router.put("/manufacturers/{manufacturer_id}", response_model=ManufacturerOut, summary="更新厂家", dependencies=[PERM_MANAGE])
async def update_manufacturer(
    manufacturer_id: int, payload: ManufacturerUpdate, db: Db, _: CurrentUser
):
    manufacturer = await get_or_404(db, Manufacturer, manufacturer_id, "厂家不存在")
    return await update_and_commit(db, manufacturer, payload.model_dump(exclude_unset=True))


@router.delete("/manufacturers/{manufacturer_id}", response_model=Message, summary="删除厂家", dependencies=[PERM_MANAGE])
async def delete_manufacturer(manufacturer_id: int, db: Db, _: CurrentUser):
    manufacturer = await get_or_404(db, Manufacturer, manufacturer_id, "厂家不存在")
    await delete_and_commit(db, manufacturer)
    return Message(message="厂家已删除")


# ----------------------------- 商品 -----------------------------
async def _with_category_name(db: AsyncSession, rows: list[Product]) -> list[ProductOut]:
    """补上分类名称（一次批量查询），供前端直接展示而不是显示分类主键。"""
    category_ids = {row.category_id for row in rows if row.category_id is not None}
    names: dict[int, str] = {}
    if category_ids:
        found = await db.execute(
            select(ProductCategory.id, ProductCategory.name).where(
                ProductCategory.id.in_(category_ids)
            )
        )
        names = {cid: name for cid, name in found.all()}
    return [
        ProductOut.model_validate(row).model_copy(
            update={"category_name": names.get(row.category_id)}
        )
        for row in rows
    ]


@router.get("/products", response_model=Page[ProductOut], summary="商品列表", dependencies=[PERM_VIEW])
async def list_products(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
    category_id: int | None = None,
    manufacturer_id: int | None = None,
    is_active: bool | None = None,
):
    stmt = select(Product).order_by(Product.id)
    if keyword:
        stmt = stmt.where(
            Product.name.ilike(f"%{keyword}%")
            | Product.sku.ilike(f"%{keyword}%")
            | Product.approval_no.ilike(f"%{keyword}%")
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if manufacturer_id is not None:
        stmt = stmt.where(Product.manufacturer_id == manufacturer_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    rows, total = await _paginate(db, stmt, params)
    return page_of(await _with_category_name(db, rows), total, params.page, params.size)


@router.get("/products/{product_id}", response_model=ProductOut, summary="商品详情", dependencies=[PERM_VIEW])
async def get_product(product_id: int, db: Db, _: CurrentUser):
    product = await get_or_404(db, Product, product_id, "商品不存在")
    (out,) = await _with_category_name(db, [product])
    return out


@router.post("/products", response_model=ProductOut, status_code=201, summary="创建商品", dependencies=[PERM_MANAGE])
async def create_product(payload: ProductCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Product).where(Product.sku == payload.sku))
    if exists:
        raise HTTPException(status_code=400, detail="SKU 已存在")
    await get_or_404(db, ProductCategory, payload.category_id, "分类不存在")
    await get_or_404(db, Manufacturer, payload.manufacturer_id, "厂家不存在")
    from app.models.master import Supplier

    await get_or_404(db, Supplier, payload.supplier_id, "供应商不存在")
    product = await create_and_commit(db, Product(**payload.model_dump()))
    return (await _with_category_name(db, [product]))[0]


@router.put("/products/{product_id}", response_model=ProductOut, summary="更新商品", dependencies=[PERM_MANAGE])
async def update_product(product_id: int, payload: ProductUpdate, db: Db, _: CurrentUser):
    product = await get_or_404(db, Product, product_id, "商品不存在")
    updated = await update_and_commit(db, product, payload.model_dump(exclude_unset=True))
    return (await _with_category_name(db, [updated]))[0]


@router.delete("/products/{product_id}", response_model=Message, summary="删除商品", dependencies=[PERM_MANAGE])
async def delete_product(product_id: int, db: Db, _: CurrentUser):
    product = await get_or_404(db, Product, product_id, "商品不存在")
    await delete_and_commit(db, product)
    return Message(message="商品已删除")


# ----------------------------- 价格历史 -----------------------------
@router.get("/products/{product_id}/prices", response_model=Page[PriceHistoryOut], summary="价格调整历史", dependencies=[PERM_VIEW])
async def list_price_history(
    product_id: int,
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
):
    await get_or_404(db, Product, product_id, "商品不存在")
    stmt = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.effective_date.desc())
    )
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.post(
    "/products/{product_id}/prices",
    response_model=PriceHistoryOut,
    status_code=201,
    summary="价格调整",
    dependencies=[PERM_MANAGE],
)
async def adjust_price(product_id: int, payload: PriceAdjustCreate, db: Db, _: CurrentUser):
    product = await get_or_404(db, Product, product_id, "商品不存在")
    old_price = product.standard_price
    record = PriceHistory(
        product_id=product_id,
        effective_date=payload.effective_date,
        old_price=old_price,
        new_price=payload.new_price,
        change_reason=payload.change_reason,
    )
    record = await create_and_commit(db, record)
    product.standard_price = payload.new_price
    await db.commit()
    return record
