"""
龙虎榜历史数据回填脚本

用途：一次性拉取过去 N 个交易日的龙虎榜数据，
      建立 lhb_alias_stock_history.csv 供胜率分析使用。

用法：
  python backfill_lhb_history.py           # 默认回填过去 30 个交易日
  python backfill_lhb_history.py 60        # 回填过去 60 个交易日
  python backfill_lhb_history.py 20260101 20260201   # 指定起止日期

注意：
  - 已存在于历史文件中的日期自动跳过，安全重复执行
  - 周六/周日自动跳过
  - 遇到节假日（接口返回空）自动跳过，不中断
  - 请求间隔 1 秒，避免被限速
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta

# ── 路径设置 ──────────────────────────────────────────────────────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(THIS_DIR, '../../')))

from lhb_detailed_analyzer import analyze_daily_lhb
from seat_winrate_analyzer import analyze_win_rates, generate_winrate_html

OUTPUT_DIR = os.path.join(THIS_DIR, 'output')
STOCK_HISTORY_FILE = os.path.join(OUTPUT_DIR, 'lhb_alias_stock_history.csv')
CONFIG_PATH = os.path.join(THIS_DIR, '../../data/lhb_config.xml')

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_trading_days(start_date: str, end_date: str) -> list[str]:
    """
    返回 [start_date, end_date] 之间所有非周末日期（YYYYMMDD 格式）。
    节假日无法在本地判断，会在请求时因接口返回空而自动跳过。
    """
    days = []
    cur = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    while cur <= end:
        if cur.weekday() < 5:   # 0=Mon … 4=Fri
            days.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return days


def already_done_dates() -> set:
    """从 lhb_alias_stock_history.csv 读取已有日期，避免重复拉取。"""
    if not os.path.exists(STOCK_HISTORY_FILE):
        return set()
    try:
        df = pd.read_csv(STOCK_HISTORY_FILE, usecols=['date'])
        return set(df['date'].astype(str).unique())
    except Exception:
        return set()


def run_backfill(trading_days: list[str], request_interval: float = 1.0):
    done = already_done_dates()
    to_run = [d for d in trading_days if d not in done]

    if not to_run:
        print("所有日期均已有数据，无需回填。")
        return

    print(f"共 {len(trading_days)} 个候选日期，已有 {len(done)} 天，需拉取 {len(to_run)} 天")
    print(f"预计耗时 ≈ {len(to_run) * 15 // 60} 分钟（每天约 15 秒）\n")

    success, skipped, failed = 0, 0, 0

    for i, date_str in enumerate(to_run, 1):
        print(f"[{i}/{len(to_run)}] ── {date_str} ──────────────────────────")
        try:
            analyze_daily_lhb(date_str, CONFIG_PATH)
            # 验证是否写入了数据
            done_after = already_done_dates()
            if date_str in done_after:
                success += 1
                print(f"  ✓ {date_str} 完成")
            else:
                skipped += 1
                print(f"  ○ {date_str} 无龙虎榜数据（可能为节假日）")
        except Exception as e:
            failed += 1
            print(f"  ✗ {date_str} 失败: {e}")

        if i < len(to_run):
            time.sleep(request_interval)

    print(f"\n{'='*50}")
    print(f"回填完成：成功 {success} 天 | 跳过(无数据) {skipped} 天 | 失败 {failed} 天")


def main():
    today = datetime.now()

    if len(sys.argv) == 3:
        # 指定起止日期
        start_str = sys.argv[1]
        end_str = sys.argv[2]
        print(f"回填模式：{start_str} → {end_str}")
    elif len(sys.argv) == 2:
        # 指定天数
        n_days = int(sys.argv[1])
        start_dt = today - timedelta(days=n_days * 2)  # 粗估，含周末
        start_str = start_dt.strftime("%Y%m%d")
        end_str = (today - timedelta(days=1)).strftime("%Y%m%d")
        print(f"回填模式：过去 {n_days} 个交易日（{start_str} → {end_str}）")
    else:
        # 默认：过去 30 个交易日
        start_dt = today - timedelta(days=60)   # 60 日历天 ≈ 30 交易日
        start_str = start_dt.strftime("%Y%m%d")
        end_str = (today - timedelta(days=1)).strftime("%Y%m%d")
        print(f"回填模式：默认过去 ~30 交易日（{start_str} → {end_str}）")

    trading_days = get_trading_days(start_str, end_str)
    print(f"候选交易日（非周末）：{len(trading_days)} 天\n")

    run_backfill(trading_days)

    # 回填完成后跑一次完整胜率分析
    print("\n开始计算席位胜率...")
    result = analyze_win_rates()
    if result:
        df_stats, df_detail = result
        generate_winrate_html(df_stats, df_detail)
        print("\n席位胜率汇总：")
        cols = ['alias', 'appearances', 'T+1_胜率(%)', 'T+1_平均收益(%)',
                'T+3_胜率(%)', 'T+3_平均收益(%)']
        print(df_stats[cols].to_string(index=False))
    else:
        print("胜率数据不足，请等更多历史数据积累后再运行。")


if __name__ == "__main__":
    main()
