from pydantic import BaseModel


class OptionOut(BaseModel):
    """下拉 / 搜索控件的候选对象：**只有主键、编码与名称**。

    这是刻意的收窄：管理页的列表接口（`/customers`、`/products`…）返回完整业务字段
    （商品成本价、客户联系方式与信用额度、供应商账期、员工手机邮箱），候选数据接口
    不需要这些字段，也不应该把它们带到所有登录账号面前（见 `api/app/api/routes/options.py`）。
    """

    id: int
    code: str | None = None
    name: str
