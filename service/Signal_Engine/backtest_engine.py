"""
席位策略回测引擎

策略逻辑：
  - 每天查看龙虎榜，跟随"历史 T+1 胜率超过阈值"的席位
  - 使用 Walk-Forward 方式：只用该日期之前的历史数据计算席位胜率
  - 等权仓位，T+1 持有后平仓
  - 需要净买入 > min_net_buy 才入场

输出指标：
  年化收益、最大回撤、Sharpe、交易胜率、交易次数
"""

import os
import sys
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(PROJECT_ROOT)

LHB_OUTPUT = os.path.join(PROJECT_ROOT, 'service/LHB_Analyse/output')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

DETAIL_PATH = os.path.join(LHB_OUTPUT, 'seat_winrate_detail.csv')


def run_backtest(
    wr_threshold: float = 55.0,    # 最低历史胜率门槛 (%)
    min_net_buy:  float = 2e7,     # 最低净买入 (元)，默认 2000 万
    hold_period:  str   = 't1',    # 持仓周期: t1 / t3 / t5
    min_samples:  int   = 5,       # 计算胜率所需最少历史样本
    initial_capital: float = 1_000_000,
):
    if not os.path.exists(DETAIL_PATH):
        print("[Backtest] 未找到历史明细文件，请先运行龙虎榜分析积累数据")
        return None

    df = pd.read_csv(DETAIL_PATH)
    return_col = f'{hold_period}_return'

    if return_col not in df.columns:
        print(f"[Backtest] 列 '{return_col}' 不存在，可选: {df.columns.tolist()}")
        return None

    df['date']    = df['date'].astype(str)
    df['net_amt'] = pd.to_numeric(df['net_amt'], errors='coerce').fillna(0)
    df[return_col] = pd.to_numeric(df[return_col], errors='coerce')
    df = df.dropna(subset=[return_col]).sort_values('date').reset_index(drop=True)

    unique_dates = sorted(df['date'].unique())
    if len(unique_dates) < 3:
        print("[Backtest] 数据天数不足（至少需要 3 天）")
        return None

    # ── Walk-Forward 回测 ──────────────────────────────────────────
    capital      = initial_capital
    equity_curve = []
    trade_log    = []

    for date in unique_dates:
        df_prior = df[df['date'] < date]
        df_today = df[df['date'] == date]

        # 计算各席位历史胜率（仅用当前日期之前的数据）
        seat_wr = {}
        for alias, grp in df_prior.groupby('alias'):
            valid = grp[return_col].dropna()
            if len(valid) >= min_samples:
                seat_wr[alias] = {
                    'win_rate':   (valid > 0).mean() * 100,
                    'avg_return': valid.mean(),
                    'n':          len(valid),
                }

        # 今日符合条件的交易
        eligible = []
        for _, row in df_today.iterrows():
            alias   = row.get('alias', '')
            net_amt = row['net_amt']
            ret     = row[return_col]

            if net_amt < min_net_buy:
                continue
            info = seat_wr.get(alias)
            if info and info['win_rate'] >= wr_threshold:
                eligible.append({'alias': alias, 'stock': row.get('stock_name', row.get('stock_code', '')), 'return': ret, 'net_amt': net_amt})

        # 等权模拟
        day_ret = 0.0
        if eligible:
            weight = 1.0 / len(eligible)
            for t in eligible:
                pnl = capital * weight * t['return'] / 100
                capital += pnl
                day_ret += weight * t['return']
                trade_log.append({'date': date, 'alias': t['alias'], 'stock': t['stock'], 'return': round(t['return'], 3)})

        equity_curve.append({'date': date, 'capital': round(capital, 2), 'n_trades': len(eligible), 'day_return': round(day_ret, 4)})

    df_equity = pd.DataFrame(equity_curve)
    df_trades = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()

    # ── 绩效指标 ────────────────────────────────────────────────────
    total_return = (capital - initial_capital) / initial_capital * 100
    n_days       = len(unique_dates)
    annual_return = ((1 + total_return / 100) ** (250 / max(n_days, 1)) - 1) * 100

    cap_arr      = df_equity['capital'].values
    rolling_max  = np.maximum.accumulate(cap_arr)
    max_drawdown = abs(((cap_arr - rolling_max) / rolling_max).min() * 100)

    daily_rets = df_equity['day_return'].values
    active_days = daily_rets[daily_rets != 0]
    if len(active_days) > 1 and active_days.std() > 0:
        sharpe = active_days.mean() / active_days.std() * np.sqrt(250)
    else:
        sharpe = 0.0

    trade_wr  = float((df_trades['return'] > 0).mean() * 100) if not df_trades.empty else 0.0
    avg_trade = float(df_trades['return'].mean()) if not df_trades.empty else 0.0

    metrics = {
        'strategy':        f"胜率>{wr_threshold}% + 净买入>{min_net_buy/1e4:.0f}万 + {hold_period.upper()}持有",
        'initial_capital': initial_capital,
        'final_capital':   round(capital, 2),
        'total_return':    round(total_return, 2),
        'annual_return':   round(annual_return, 2),
        'max_drawdown':    round(max_drawdown, 2),
        'sharpe':          round(sharpe, 2),
        'n_trades':        len(trade_log),
        'trade_win_rate':  round(trade_wr, 1),
        'avg_trade_return': round(avg_trade, 3),
        'n_days':          n_days,
    }

    # ── 保存 ────────────────────────────────────────────────────────
    df_equity.to_csv(os.path.join(OUTPUT_DIR, 'backtest_equity.csv'), index=False)
    if not df_trades.empty:
        df_trades.to_csv(os.path.join(OUTPUT_DIR, 'backtest_trades.csv'), index=False, encoding='utf-8-sig')
    with open(os.path.join(OUTPUT_DIR, 'backtest_metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"[Backtest] {metrics['strategy']}")
    print(f"[Backtest] 总收益 {metrics['total_return']:+.1f}% | 年化 {metrics['annual_return']:+.1f}% | 最大回撤 {metrics['max_drawdown']:.1f}% | Sharpe {metrics['sharpe']:.2f}")
    print(f"[Backtest] 交易 {metrics['n_trades']} 笔 | 胜率 {metrics['trade_win_rate']:.1f}% | 单笔均收益 {metrics['avg_trade_return']:+.3f}%")

    return metrics, df_equity, df_trades


if __name__ == '__main__':
    result = run_backtest()
    if result:
        metrics, _, _ = result
