from fastapi import APIRouter

from app.api.routes import (
    auth,
    avatars,
    customers,
    finance,
    gsp,
    inventory,
    org,
    products,
    purchase,
    reports,
    returns,
    sales,
    suppliers,
    system,
    warehouses,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(avatars.router, prefix="/avatars", tags=["头像"])
api_router.include_router(system.router, tags=["系统管理"])
api_router.include_router(org.router, tags=["组织与员工"])
api_router.include_router(customers.router, prefix="/customers", tags=["客户管理"])
api_router.include_router(products.router, tags=["商品管理"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["供应商管理"])
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["仓库管理"])
api_router.include_router(purchase.router, prefix="/purchase-orders", tags=["采购管理"])
api_router.include_router(sales.router, prefix="/sales-orders", tags=["销售管理"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["库存管理"])
api_router.include_router(returns.router, prefix="/sales-returns", tags=["退货管理"])
api_router.include_router(finance.router, tags=["财务与收款"])
api_router.include_router(reports.router, prefix="/reports", tags=["报表与分析"])
api_router.include_router(gsp.router, prefix="/gsp", tags=["GSP 合规"])
