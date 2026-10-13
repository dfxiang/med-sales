from datetime import date
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# 测试环境统一配置系统对接 API Key（支持多个，逗号分隔）
os.environ.setdefault("SYS_API_KEYS", "test-api-key-1,test-api-key-2")

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_password
from app.main import app
from app.models.inventory import Inventory
from app.models.master import (
    Customer,
    Manufacturer,
    Product,
    ProductCategory,
    Supplier,
    Warehouse,
)
from app.models.org import Department, Employee
from app.models.system import Permission, Role, User


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    """预置基础主数据：管理员账号、部门、员工、仓库、分类、厂家、供应商、商品、客户、库存。"""
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    role = Role(name="管理员", description="系统管理员")
    db_session.add(role)
    await db_session.flush()
    perm = Permission(code="all", name="全部权限")
    db_session.add(perm)
    await db_session.flush()
    from app.models.system import role_permissions, user_roles

    await db_session.execute(
        user_roles.insert().values(user_id=admin.id, role_id=role.id)
    )
    await db_session.execute(
        role_permissions.insert().values(role_id=role.id, permission_id=perm.id)
    )

    department = Department(code="D001", name="销售管理部", description="销售管理")
    db_session.add(department)
    await db_session.flush()

    employee = Employee(
        code="E0001",
        name="张三",
        gender="男",
        department_id=department.id,
        position="销售代表",
        hire_date=date(2022, 1, 1),
        employment_status="在职",
    )
    db_session.add(employee)
    await db_session.flush()

    warehouse = Warehouse(
        code="WH-001",
        name="上海中心仓",
        province="上海市",
        city="上海",
        has_cold_chain=True,
        status="正常",
    )
    db_session.add(warehouse)
    await db_session.flush()

    category = ProductCategory(code="CAT-DRUG", name="化学药品", is_active=True)
    db_session.add(category)
    await db_session.flush()

    manufacturer = Manufacturer(name="测试制药", country="中国")
    db_session.add(manufacturer)
    await db_session.flush()

    supplier = Supplier(code="SUP001", name="测试供应商", credit_days=30, status="合作中")
    db_session.add(supplier)
    await db_session.flush()

    product = Product(
        sku="SKU-TEST-001",
        name="测试药品",
        category_id=category.id,
        manufacturer_id=manufacturer.id,
        supplier_id=supplier.id,
        approval_no="国药准字TEST001",
        specification="10mg*20片/盒",
        unit="盒",
        storage_condition="常温",
        is_cold_chain=False,
        shelf_life_months=24,
        cost_price=10,
        standard_price=15,
        is_active=True,
        listed_date=date(2022, 1, 1),
    )
    db_session.add(product)
    await db_session.flush()

    customer = Customer(
        code="C00001",
        name="测试医院",
        customer_type="三级医院",
        coop_level="重点客户",
        province="上海市",
        city="上海",
        credit_limit=100000,
        status="正常",
    )
    db_session.add(customer)
    await db_session.flush()

    db_session.add(
        Inventory(
            warehouse_id=warehouse.id,
            product_id=product.id,
            quantity=1000,
            safety_stock=50,
        )
    )
    await db_session.commit()

    return {
        "admin_id": admin.id,
        "department_id": department.id,
        "employee_id": employee.id,
        "warehouse_id": warehouse.id,
        "category_id": category.id,
        "manufacturer_id": manufacturer.id,
        "supplier_id": supplier.id,
        "product_id": product.id,
        "customer_id": customer.id,
    }


@pytest_asyncio.fixture
async def client(db_engine, seed_data):
    """FastAPI 测试客户端（覆盖数据库依赖为内存 SQLite）。"""

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ids(seed_data) -> dict:
    return seed_data
