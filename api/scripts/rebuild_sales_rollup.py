"""重建 / 对账销售报表汇总表。

用法::

    .venv/bin/python scripts/rebuild_sales_rollup.py                    # 全量重建
    .venv/bin/python scripts/rebuild_sales_rollup.py --check            # 只对账，不写库
    .venv/bin/python scripts/rebuild_sales_rollup.py --date 2026-07-30  # 只重算某天

什么时候需要跑：

* **首次上线（或生成 mock 数据）后回填**——窗口期内汇总表是空的，报表会显示为 0；
* 夜间对账：日常增量维护的兜底，任何漏掉的写路径都会在这里被对账发现；
* 有人绕过 API 直接改库（批量导入、手工 UPDATE）之后。

对账口径见 ``app/services/rollup.py:check_consistency``。
"""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal, init_db  # noqa: E402
from app.services.rollup import (  # noqa: E402
    check_consistency,
    keys_for_dates,
    rebuild_all,
    refresh_rollups,
)


def _report_issues(issues: list[str]) -> None:
    print("对账不一致：")
    for issue in issues:
        print(f"  - {issue}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="重建销售报表汇总表")
    parser.add_argument(
        "--date",
        action="append",
        dest="dates",
        default=[],
        metavar="YYYY-MM-DD",
        help="只重算指定业务日期（可重复传入），省略则全量重建",
    )
    parser.add_argument("--check", action="store_true", help="只对账，不修改数据")
    args = parser.parse_args()

    await init_db()
    async with AsyncSessionLocal() as db:
        if args.check:
            issues = await check_consistency(db)
            if issues:
                _report_issues(issues)
                sys.exit(1)
            print("对账通过：5 张汇总表与明细表一致")
            return

        if args.dates:
            dates = {date.fromisoformat(value) for value in args.dates}
            keys = await keys_for_dates(db, dates)
            await refresh_rollups(db, keys)
            print(
                f"已重算 {len(dates)} 天：商品 {len(keys.product_ids)} 个、"
                f"客户 {len(keys.customer_ids)} 个、销售员 {len(keys.employee_ids)} 个"
            )
        else:
            await rebuild_all(db)
            print("已全量重建 5 张销售汇总表")
        await db.commit()

        issues = await check_consistency(db)
        if issues:
            _report_issues(issues)
            sys.exit(1)
        print("对账通过：5 张汇总表与明细表一致")


if __name__ == "__main__":
    asyncio.run(main())
