"""一键执行：创建数据库 -> 生成 mock 数据 -> 校验。

连接参数见 db_config.py（默认连本项目的 `demo-db` 容器：127.0.0.1:5688），
数据规模/区间/种子等生成参数见 mock_params.py。

用法：
    python run_all.py                                   # 数据库不存在时创建并初始化
    python run_all.py --reset                           # 删除已有 medsalesdb 后重新初始化
    python run_all.py --reset --seed 20260101           # 换一批数据
    python run_all.py --reset --start-date 2023-01-01 --end-date 2025-12-31
"""

import argparse
import subprocess
import sys
from pathlib import Path

from db_config import DB_NAME, target
from mock_params import END_DATE, SEED, START_DATE

BASE_DIR = Path(__file__).resolve().parent


def run_script(name: str, *args: str) -> None:
    cmd = [sys.executable, str(BASE_DIR / name), *args]
    print(f"\n==================== 执行 {name} ====================")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="medsalesdb 演示数据库一键初始化")
    parser.add_argument("--reset", action="store_true", help="删除已有 medsalesdb 后重建")
    parser.add_argument("--seed", type=int, default=None,
                        help=f"随机种子，默认 {SEED}（见 mock_params.py）")
    parser.add_argument("--start-date", default=None,
                        help=f"数据起始日期 YYYY-MM-DD，默认 {START_DATE}")
    parser.add_argument("--end-date", default=None,
                        help=f"数据结束日期 YYYY-MM-DD，默认 {END_DATE}")
    args = parser.parse_args()

    reset_args = ["--reset"] if args.reset else []
    seed_args = ["--seed", str(args.seed)] if args.seed is not None else []
    range_args = []
    if args.start_date:
        range_args += ["--start-date", args.start_date]
    if args.end_date:
        range_args += ["--end-date", args.end_date]

    print(f"[run_all] 目标数据库：{target()}")
    run_script("create_database.py", *reset_args)
    run_script("generate_mock_data.py", *seed_args, *range_args)
    # verify 只校验区间（种子不影响校验口径）
    run_script("verify_database.py", *range_args)
    print(f"\n[run_all] 全部完成：{DB_NAME} 数据库已创建并保留 "
          f"{args.start_date or START_DATE} ~ {args.end_date or END_DATE} 演示数据。")


if __name__ == "__main__":
    main()
