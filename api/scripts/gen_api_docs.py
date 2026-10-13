"""根据 OpenAPI 规范生成中文接口文档（markdown）。

用法：
    .venv/bin/python scripts/gen_api_docs.py

输出：
    ../docs/API接口文档.md
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


# 常见字段的中文名称映射（用于参数表）
FIELD_LABELS = {
    "id": "ID",
    "user_id": "用户 ID",
    "username": "用户名",
    "password": "密码",
    "display_name": "显示名称",
    "avatar_url": "头像地址",
    "old_password": "原密码",
    "new_password": "新密码",
    "confirm_password": "确认新密码",
    "password_hash": "密码哈希",
    "is_active": "是否启用",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "code": "编码",
    "name": "名称",
    "description": "说明",
    "remark": "备注",
    "gender": "性别",
    "phone": "电话",
    "email": "邮箱",
    "department_id": "部门 ID",
    "department_name": "部门名称",
    "position": "职位",
    "manager_id": "上级员工 ID",
    "hire_date": "入职日期",
    "employment_status": "在职状态",
    "customer_id": "客户 ID",
    "customer_name": "客户名称",
    "customer_code": "客户编码",
    "customer_type": "客户类型",
    "coop_level": "合作等级",
    "contact_person": "联系人",
    "province": "省份",
    "city": "城市",
    "address": "地址",
    "shipping_address": "收货地址",
    "license_no": "证照编号",
    "credit_limit": "信用额度",
    "status": "状态",
    "supplier_id": "供应商 ID",
    "supplier_name": "供应商名称",
    "credit_days": "账期天数",
    "manufacturer_id": "生产厂家 ID",
    "manufacturer_name": "厂家名称",
    "category_id": "分类 ID",
    "category_name": "分类名称",
    "sort_order": "排序",
    "sku": "SKU",
    "approval_no": "批准文号",
    "specification": "规格",
    "unit": "单位",
    "dosage_form": "剂型",
    "storage_condition": "储存条件",
    "is_cold_chain": "是否冷链",
    "shelf_life_months": "有效期（月）",
    "cost_price": "成本价",
    "standard_price": "标准售价",
    "unit_price": "成交单价",
    "unit_cost": "成本单价",
    "price": "价格",
    "old_price": "调整前价格",
    "new_price": "调整后价格",
    "change_reason": "调价原因",
    "effective_date": "生效日期",
    "warehouse_id": "仓库 ID",
    "warehouse_name": "仓库名称",
    "manager_name": "负责人",
    "has_cold_chain": "具备冷链",
    "order_id": "订单 ID",
    "order_no": "订单编号",
    "order_date": "下单日期",
    "order_count": "订单数",
    "order_status": "订单状态",
    "item_count": "商品行数",
    "total_quantity": "总数量",
    "subtotal_amount": "小计金额",
    "discount_amount": "优惠金额",
    "discount_rate": "折扣率",
    "total_amount": "总金额",
    "paid_amount": "已收金额",
    "cost_amount": "成本金额",
    "invoice_type": "开票类型",
    "settlement_method": "结算方式",
    "delivery_type": "配送方式",
    "delivery_date": "发货日期",
    "quantity": "数量",
    "received_quantity": "实收数量",
    "received_date": "实收日期",
    "expected_date": "预计到货日期",
    "amount": "金额",
    "line_amount": "行金额",
    "items": "明细列表",
    "product_id": "商品 ID",
    "product_name": "商品名称",
    "sold_quantity": "销量",
    "sales_amount": "销售额",
    "gross_profit": "毛利",
    "profit_amount": "毛利",
    "employee_id": "员工 ID",
    "employee_code": "工号",
    "employee_name": "员工姓名",
    "customer_count": "客户数",
    "return_id": "退货单 ID",
    "return_no": "退货单编号",
    "return_date": "退货日期",
    "sales_order_id": "原销售订单 ID",
    "reason": "原因",
    "payment_id": "收款记录 ID",
    "payment_date": "付款日期",
    "payment_method": "付款方式",
    "receivable": "应收金额",
    "days_overdue": "逾期天数",
    "sale_date": "销售日期",
    "month": "月份",
    "prev_month_amount": "上月销售额",
    "amount_growth_rate": "环比增速（%）",
    "today_order_count": "今日订单数",
    "today_sales_amount": "今日销售额",
    "today_profit": "今日毛利",
    "month_order_count": "本月订单数",
    "month_sales_amount": "本月销售额",
    "month_profit": "本月毛利",
    "low_stock_count": "库存不足商品数",
    "pending_return_count": "待处理退货单数",
    "total_receivable": "应收总额",
    "stock_status": "库存状态",
    "stock_value": "库存价值",
    "safety_stock": "安全库存",
    "stock_diff": "与安全库存差值",
    "movement_type": "流水类型",
    "movement_date": "变动日期",
    "ref_table": "关联表名",
    "ref_id": "关联明细 ID",
    "created_by": "经办人 ID",
    "inventory_id": "库存记录 ID",
    "batch_id": "批次 ID",
    "batch_no": "批号",
    "production_date": "生产日期",
    "expiry_date": "有效期至",
    "certificate_id": "证照 ID",
    "entity_type": "关联对象类型",
    "entity_id": "关联对象 ID",
    "cert_type": "证照类型",
    "cert_no": "证照编号",
    "valid_from": "生效日期",
    "valid_to": "到期日期",
    "api_key": "API Key",
    "access_token": "访问令牌",
    "token_type": "令牌类型",
    "page": "页码",
    "size": "每页条数",
    "total": "总条数",
    "keyword": "关键词",
    "start_date": "开始日期",
    "end_date": "结束日期",
    "days": "天数",
    "login": "登录",
    "access_token_expire_minutes": "令牌有效期（分钟）",
}

TYPE_LABELS = {
    "string": "字符串",
    "integer": "整数",
    "number": "数值",
    "boolean": "布尔",
    "array": "数组",
    "object": "对象",
    "null": "空",
}


def ref_name(schema: dict) -> str:
    ref = schema.get("$ref", "")
    return ref.rsplit("/", 1)[-1] if ref else ""


def resolve(schema: dict, components: dict) -> dict:
    seen = 0
    while "$ref" in schema and seen < 10:
        name = ref_name(schema)
        schema = components.get(name, {})
        seen += 1
    return schema


def field_type(schema: dict, components: dict) -> str:
    name = ref_name(schema)
    if name:
        return name
    schema = resolve(schema, components)
    if "anyOf" in schema:
        for part in schema["anyOf"]:
            resolved = resolve(part, components)
            if resolved.get("type") != "null":
                return field_type(part, components)
        return "字符串"
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    if t == "array":
        return field_type(schema.get("items", {}), components) + "[]"
    fmt = schema.get("format")
    if t == "string" and fmt == "date":
        return "日期"
    if t == "string" and fmt == "date-time":
        return "日期时间"
    return TYPE_LABELS.get(t, t or "对象")


def build_example(schema: dict, components: dict, depth: int = 0) -> object:
    if depth > 4:
        return None
    name = ref_name(schema)
    if name:
        schema = components.get(name, {})
    schema = resolve(schema, components)
    if "example" in schema:
        return schema["example"]
    if "default" in schema and schema["default"] is not None:
        return schema["default"]
    if "enum" in schema:
        return schema["enum"][0]
    if "allOf" in schema:
        merged: dict = {}
        for part in schema["allOf"]:
            merged.update(resolve(part, components))
        return build_example(merged, components, depth + 1)
    if "anyOf" in schema:
        for part in schema["anyOf"]:
            resolved = resolve(part, components)
            if resolved.get("type") != "null":
                return build_example(part, components, depth + 1)
        return None
    if "properties" in schema:
        return {
            k: build_example(v, components, depth + 1)
            for k, v in schema["properties"].items()
        }
    t = schema.get("type")
    if t == "array":
        return [build_example(schema.get("items", {}), components, depth + 1)]
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return False
    fmt = schema.get("format")
    if fmt == "date":
        return "2026-01-01"
    if fmt == "date-time":
        return "2026-09-01T00:00:00"
    return "string"


def field_rows(schema: dict, components: dict) -> list[tuple[str, str, str, str]]:
    schema = resolve(schema, components)
    if "allOf" in schema:
        merged: dict = {"required": [], "properties": {}}
        for part in schema["allOf"]:
            p = resolve(part, components)
            merged["properties"].update(p.get("properties", {}))
            merged["required"] += p.get("required", [])
        schema = merged
    required = set(schema.get("required", []))
    rows = []
    for key, sub in (schema.get("properties") or {}).items():
        label = FIELD_LABELS.get(key, key)
        desc = sub.get("description", "")
        if "enum" in resolve(sub, components):
            enums = "、".join(str(e) for e in resolve(sub, components)["enum"])
            desc = f"{desc}（可选值：{enums}）" if desc else f"可选值：{enums}"
        rows.append(
            (
                key,
                field_type(sub, components),
                "是" if key in required else "否",
                desc or label,
            )
        )
    return rows


def param_rows(parameters: list[dict], components: dict) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for p in parameters:
        where = "路径" if p.get("in") == "path" else "查询"
        schema = p.get("schema", {})
        required = "是" if p.get("required") else "否"
        default = ""
        if "default" in schema and schema["default"] is not None:
            default = str(schema["default"])
        desc = p.get("description", "")
        rows.append(
            (
                p["name"],
                where,
                field_type(schema, components),
                required,
                default,
                desc or FIELD_LABELS.get(p["name"], ""),
            )
        )
    return rows


def render_table(headers: list[str], rows: list[tuple]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def method_style(method: str) -> str:
    colors = {
        "GET": "GET",
        "POST": "POST",
        "PUT": "PUT",
        "DELETE": "DELETE",
    }
    return colors.get(method.upper(), method.upper())


def iter_api_routes(routes, prefix: str = ""):
    """遍历路由表，展开 FastAPI 的「延迟包含」包装（_IncludedRouter），产出 (完整路径, 路由)。"""
    for route in routes:
        if type(route).__name__ == "_IncludedRouter":
            context = getattr(route, "include_context", None)
            nested_prefix = prefix + (getattr(context, "prefix", "") or "")
            inner = getattr(route, "original_router", None)
            if inner is not None:
                yield from iter_api_routes(inner.routes, nested_prefix)
            continue
        path = getattr(route, "path", None)
        if not path:
            continue
        yield prefix + path, route


def route_permission_map() -> dict[tuple[str, str], tuple[str, ...]]:
    """(路径, 方法) → 所需权限编码。

    路由上的 `dependencies=[Depends(require_permission("x"))]` 会在依赖函数上留下
    `__permission_codes__` 标记，这里据此反查（与运行期校验共用同一处定义）。
    """
    mapping: dict[tuple[str, str], tuple[str, ...]] = {}
    for path, route in iter_api_routes(app.routes):
        methods = getattr(route, "methods", None)
        dependant = getattr(route, "dependant", None)
        if not methods or dependant is None:
            continue
        codes: list[str] = []
        for sub in dependant.dependencies:
            for code in getattr(sub.call, "__permission_codes__", ()) or ():
                if code not in codes:
                    codes.append(code)
        if not codes:
            continue
        for method in methods:
            mapping[(path, method.upper())] = tuple(codes)
    return mapping


def permission_text(codes: tuple[str, ...]) -> str:
    if not codes:
        return "—"
    return " 或 ".join(f"`{code}`" for code in codes)


def build_doc() -> str:
    spec = app.openapi()
    components = spec.get("components", {}).get("schemas", {})
    paths = spec["paths"]
    perm_map = route_permission_map()
    tags_order: list[str] = []
    tag_titles = {
        "认证": "一、认证",
        "系统管理": "二、系统管理",
        "组织与员工": "三、组织与员工",
        "客户管理": "四、客户管理",
        "商品管理": "五、商品管理",
        "供应商管理": "六、供应商管理",
        "仓库管理": "七、仓库管理",
        "采购管理": "八、采购管理",
        "销售管理": "九、销售管理",
        "库存管理": "十、库存管理",
        "退货管理": "十一、退货管理",
        "财务与收款": "十二、财务与收款",
        "报表与分析": "十三、报表与分析",
        "GSP 合规": "十四、GSP 合规",
    }

    # 收集模块与接口
    operations = []
    for path, methods in paths.items():
        for method, op in methods.items():
            tag = (op.get("tags") or ["其他"])[0]
            if tag not in tags_order:
                tags_order.append(tag)
            operations.append((tag, path, method, op))

    lines: list[str] = []
    lines.append("# 医药销售管理系统 API 接口文档")
    lines.append("")
    lines.append("> 自动生成：基于 OpenAPI 规范（FastAPI）")
    lines.append("")
    lines.append("## 一、文档说明")
    lines.append("")
    lines.append("| 项目 | 说明 |")
    lines.append("| --- | --- |")
    lines.append(f"| 接口版本 | {spec.get('info', {}).get('version', '0.1.0')} |")
    lines.append("| 基础地址（容器部署） | http://127.0.0.1:8001/api |")
    lines.append("| 基础地址（本地开发） | http://127.0.0.1:8000/api |")
    lines.append("| 数据格式 | JSON（UTF-8） |")
    lines.append("| 在线文档 | http://127.0.0.1:8001/docs（Swagger UI） |")
    lines.append("")
    lines.append("### 1. 认证方式")
    lines.append("")
    lines.append("除「登录」「健康检查」「通过 API Key 获取令牌」外，所有接口均需携带令牌：")
    lines.append("")
    lines.append("```")
    lines.append("Authorization: Bearer <access_token>")
    lines.append("```")
    lines.append("")
    lines.append("令牌获取方式：")
    lines.append("")
    lines.append("1. 用户登录：`POST /api/auth/login`（用户名 + 密码）")
    lines.append("2. 系统对接：`POST /api/auth/token`（环境变量 SYS_API_KEYS 配置的 API Key + 用户 ID）")
    lines.append("")
    lines.append("### 2. 分页参数")
    lines.append("")
    lines.append("| 参数 | 类型 | 必填 | 默认 | 说明 |")
    lines.append("| --- | --- | --- | --- | --- |")
    lines.append("| page | 整数 | 否 | 1 | 页码，从 1 开始 |")
    lines.append("| size | 整数 | 否 | 20 | 每页条数，最大 200 |")
    lines.append("")
    lines.append("分页响应结构：")
    lines.append("")
    lines.append("```json")
    lines.append('{"items": [], "total": 0, "page": 1, "size": 20}')
    lines.append("```")
    lines.append("")
    lines.append("### 3. 错误响应")
    lines.append("")
    lines.append("接口错误统一返回：`{\"detail\": \"错误描述\"}`，常见状态码：")
    lines.append("")
    lines.append("| 状态码 | 含义 |")
    lines.append("| --- | --- |")
    lines.append("| 200 | 成功 |")
    lines.append("| 201 | 创建成功 |")
    lines.append("| 400 | 请求参数错误 / 业务规则不满足 |")
    lines.append("| 401 | 未认证或令牌无效 / API Key 无效 |")
    lines.append("| 403 | 已登录但缺少接口所需权限 |")
    lines.append("| 404 | 资源不存在 |")
    lines.append("| 422 | 请求体校验失败 |")
    lines.append("")
    lines.append("### 4. 权限校验")
    lines.append("")
    lines.append("接口在鉴权之外还会做**权限校验**：账号需经角色继承到对应权限编码，否则返回 403。")
    lines.append("")
    lines.append("- 权限编码约定：`模块:动作` 或 `模块:对象:动作`，例如 `sales:view`、`system:user:manage`；")
    lines.append("- 内置通配权限 `all`（绑定在「管理员」角色上）：拥有它即可访问全部接口；")
    lines.append("- 当前登录账号的权限编码可调用 `GET /api/auth/me` 获取（返回 `permissions` 数组）；")
    lines.append("- 权限清单由 `permissions` 表维护，接口启动时会幂等补齐内置清单，详见 [权限控制说明](./权限控制说明.md)。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 二、接口索引")
    lines.append("")
    lines.append("| 模块 | 接口数 |")
    lines.append("| --- | --- |")
    for tag in tags_order:
        count = sum(1 for t, _, _, _ in operations if t == tag)
        lines.append(f"| {tag_titles.get(tag, tag)} | {count} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    for tag in tags_order:
        lines.append(f"## {tag_titles.get(tag, tag)}")
        lines.append("")
        tag_ops = [o for o in operations if o[0] == tag]
        lines.append("| 方法 | 路径 | 接口名称 | 认证 | 所需权限 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for _, path, method, op in tag_ops:
            auth = "需要" if op.get("security") else "不需要"
            perms = permission_text(perm_map.get((path, method.upper()), ()))
            lines.append(
                f"| {method_style(method)} | `{path}` | {op.get('summary', '')} | {auth} | {perms} |"
            )
        lines.append("")

        for _, path, method, op in tag_ops:
            lines.append(f"### {method_style(method)} {path}")
            lines.append("")
            lines.append(f"**接口名称：** {op.get('summary', '')}")
            lines.append("")
            if op.get("description"):
                lines.append(f"**说明：** {op['description']}")
                lines.append("")
            lines.append(f"**认证：** {'需要 Bearer Token' if op.get('security') else '不需要'}")
            lines.append("")
            perms = perm_map.get((path, method.upper()), ())
            if perms:
                lines.append(f"**所需权限：** {permission_text(perms)}")
                lines.append("")

            params = op.get("parameters", [])
            if params:
                lines.append("**请求参数：**")
                lines.append("")
                lines.append(
                    render_table(
                        ["参数名", "位置", "类型", "必填", "默认值", "说明"],
                        param_rows(params, components),
                    )
                )
                lines.append("")

            body = op.get("requestBody", {})
            content = body.get("content", {}).get("application/json", {})
            if content.get("schema"):
                schema = content["schema"]
                lines.append("**请求体：**")
                lines.append("")
                lines.append(
                    render_table(
                        ["字段", "类型", "必填", "说明"],
                        field_rows(schema, components),
                    )
                )
                lines.append("")
                example = build_example(schema, components)
                lines.append("**请求示例：**")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(example, ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")

            resp_schema = None
            resp200 = op.get("responses", {}).get("200", {})
            if "content" in resp200:
                resp_schema = resp200["content"].get("application/json", {}).get("schema")
            if resp_schema is None:
                resp201 = op.get("responses", {}).get("201", {})
                if "content" in resp201:
                    resp_schema = resp201["content"].get("application/json", {}).get("schema")
            if resp_schema:
                lines.append("**响应示例（200/201）：**")
                lines.append("")
                lines.append("```json")
                lines.append(
                    json.dumps(
                        build_example(resp_schema, components),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                lines.append("```")
                lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    doc = build_doc()
    out = Path(__file__).resolve().parents[2] / "docs" / "API接口文档.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    print(f"已生成：{out}（{len(doc.splitlines())} 行）")


if __name__ == "__main__":
    main()
