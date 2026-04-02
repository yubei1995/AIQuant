"""
今日交易信号评分器

读取当日龙虎榜数据 + 历史席位胜率 → 生成带评分的可执行信号列表

评分逻辑 (满分 10 分):
  - 历史 T+1 胜率 (0-5 分): 胜率越高得分越高，50% 以下得 0 分
  - 净买入金额 (0-2 分): 5000 万满分
  - 样本可信度 (0-2 分): 20 个样本满分
  - 历史平均收益 (0-1 分): 正收益得 1 分

信号等级:
  8+ 分 → 强烈关注
  6-8 分 → 关注
  6 分以下 → 观望
"""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(PROJECT_ROOT)

LHB_OUTPUT = os.path.join(PROJECT_ROOT, 'service/LHB_Analyse/output')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _load(path):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame()


def _score(alias, net_amt, winrate_map):
    info = winrate_map.get(alias, {})
    t1_wr  = info.get('T+1_胜率(%)')
    t1_avg = info.get('T+1_平均收益(%)')
    n      = info.get('T+1_样本数', 0)

    t1_wr  = float(t1_wr)  if t1_wr  is not None and str(t1_wr)  != 'nan' else 50.0
    t1_avg = float(t1_avg) if t1_avg is not None and str(t1_avg) != 'nan' else 0.0
    n      = int(n)        if n      is not None and str(n)      != 'nan' else 0

    wr_score   = max(0.0, min(5.0, (t1_wr - 50) / 20 * 5))   # 50%→0, 70%→5
    net_score  = min(2.0, float(net_amt) / 50_000_000 * 2)    # 5000万 满分
    conf_score = min(2.0, n / 20 * 2)                          # 20样本 满分
    ret_score  = 1.0 if t1_avg > 0 else 0.0

    return round(min(10.0, wr_score + net_score + conf_score + ret_score), 1)


def score_today_signals() -> pd.DataFrame:
    df_lhb = _load(os.path.join(LHB_OUTPUT, 'lhb_latest_alias_detail.csv'))
    df_wr  = _load(os.path.join(LHB_OUTPUT, 'seat_winrate.csv'))

    if df_lhb.empty:
        print("[SignalEngine] 无今日龙虎榜数据")
        return pd.DataFrame()

    # 只看净买入
    df_lhb = df_lhb[df_lhb['net_amt'] > 0].copy()

    # 建立胜率查找表
    winrate_map = {}
    if not df_wr.empty:
        for _, r in df_wr.iterrows():
            winrate_map[r['alias']] = r.to_dict()

    records = []
    for _, row in df_lhb.iterrows():
        alias   = str(row.get('alias', '')).strip()
        net_amt = float(row.get('net_amt', 0))
        if not alias:
            continue

        info   = winrate_map.get(alias, {})
        t1_wr  = info.get('T+1_胜率(%)')
        t3_wr  = info.get('T+3_胜率(%)')
        t1_avg = info.get('T+1_平均收益(%)')
        t1_n   = info.get('T+1_样本数', 0)

        score = _score(alias, net_amt, winrate_map)

        if score >= 8:
            level, level_color = '强烈关注', '#c0392b'
        elif score >= 6:
            level, level_color = '关注',     '#e67e22'
        else:
            level, level_color = '观望',     '#7f8c8d'

        def _fmt_pct(v):
            try: return f"{float(v):.1f}%"
            except: return '数据积累中'

        def _fmt_ret(v):
            try: return f"{float(v):+.2f}%"
            except: return '-'

        records.append({
            'score':       score,
            'level':       level,
            'level_color': level_color,
            'alias':       alias,
            'category':    row.get('category', ''),
            'stock_code':  str(row.get('stock_code', '')),
            'stock_name':  str(row.get('stock_name', '')),
            'net_amt':     net_amt,
            'buy_amt':     float(row.get('buy_amt', 0)),
            'T+1_胜率':    _fmt_pct(t1_wr),
            'T+3_胜率':    _fmt_pct(t3_wr),
            'T+1_均收益':  _fmt_ret(t1_avg),
            '样本数':       int(t1_n) if t1_n and str(t1_n) != 'nan' else 0,
        })

    if not records:
        print("[SignalEngine] 今日无可评分信号")
        return pd.DataFrame()

    df_out = pd.DataFrame(records).sort_values('score', ascending=False).reset_index(drop=True)
    df_out.to_csv(os.path.join(OUTPUT_DIR, 'today_signals.csv'), index=False, encoding='utf-8-sig')
    print(f"[SignalEngine] {len(df_out)} 条信号已评分")
    return df_out


if __name__ == '__main__':
    df = score_today_signals()
    if not df.empty:
        print(df[['score', 'level', 'alias', 'stock_name', 'T+1_胜率', 'T+1_均收益', '样本数']].to_string(index=False))
