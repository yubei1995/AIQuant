"""
龙虎榜席位胜率分析器

读取历史龙虎榜席位-个股记录，计算每个命名席位（游资别名）
在净买入后 T+1、T+3、T+5 的历史胜率与平均收益。

输出：
  - output/seat_winrate.csv          : 每席位汇总胜率表
  - output/seat_winrate_detail.csv   : 每笔交易明细
  - output/seat_winrate_report.html  : 可视化 HTML 报告
  - share_reports/seat_winrate_report.html : 共享报告副本
"""

import os
import sys
import json
import concurrent.futures
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.data_fetch.stock_data import StockDataFetcher

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
HISTORY_FILE = os.path.join(OUTPUT_DIR, 'lhb_alias_stock_history.csv')
WINRATE_CSV = os.path.join(OUTPUT_DIR, 'seat_winrate.csv')
DETAIL_CSV = os.path.join(OUTPUT_DIR, 'seat_winrate_detail.csv')
REPORT_FILE = os.path.join(OUTPUT_DIR, 'seat_winrate_report.html')
SHARED_REPORT_FILE = os.path.join(os.path.dirname(__file__), '../../share_reports/seat_winrate_report.html')

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Price fetching helpers
# ---------------------------------------------------------------------------

def _fetch_price_window(fetcher: StockDataFetcher, code: str, date_str: str) -> pd.DataFrame | None:
    """
    Fetch closing prices starting from date_str for ~14 calendar days
    (enough to cover T+5 trading days including weekends / holidays).
    Returns a DataFrame sorted by 日期, or None on failure.
    """
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        end_str = (dt + timedelta(days=14)).strftime("%Y%m%d")
        df = fetcher.get_stock_hist(code, start_date=date_str, end_date=end_str)
        if df is None or df.empty:
            return None
        df['日期'] = pd.to_datetime(df['日期'])
        df['收盘'] = pd.to_numeric(df['收盘'], errors='coerce')
        return df.sort_values('日期').reset_index(drop=True)
    except Exception:
        return None


def _calc_returns(df: pd.DataFrame) -> dict:
    """
    Given a price window starting at T+0, return T+1 / T+3 / T+5 returns (%).
    """
    result = {}
    if df is None or len(df) < 2:
        return result
    t0 = df.iloc[0]['收盘']
    if pd.isna(t0) or t0 <= 0:
        return result
    for n, key in [(1, 't1'), (3, 't3'), (5, 't5')]:
        if len(df) > n:
            tn = df.iloc[n]['收盘']
            if pd.notnull(tn) and tn > 0:
                result[key] = round((tn - t0) / t0 * 100, 3)
    return result


def _fetch_task(args):
    """Worker for thread pool: returns (cache_key, df_or_None)."""
    fetcher, code, date_str, cache_key = args
    return cache_key, _fetch_price_window(fetcher, code, date_str)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_win_rates(max_workers: int = 8):
    """
    Main function. Returns (df_stats, df_detail) or None on failure.
    """
    if not os.path.exists(HISTORY_FILE):
        print(f"[WinRate] History file not found: {HISTORY_FILE}")
        print("[WinRate] Run lhb_detailed_analyzer.py first to build history.")
        return None

    df_history = pd.read_csv(HISTORY_FILE)
    if df_history.empty:
        print("[WinRate] History file is empty.")
        return None

    # Only analyse records where the seat was a net buyer
    df_buy = df_history[df_history['net_amt'] > 0].copy()
    df_buy['date'] = df_buy['date'].astype(str)
    df_buy['stock_code'] = df_buy['stock_code'].astype(str)

    # Strip market prefix for price fetching
    def strip_prefix(code):
        return code[2:] if code.startswith(('sh', 'sz', 'bj')) else code

    df_buy['clean_code'] = df_buy['stock_code'].apply(strip_prefix)
    df_buy['cache_key'] = df_buy['clean_code'] + '_' + df_buy['date']

    unique_keys = df_buy[['cache_key', 'clean_code', 'date']].drop_duplicates()
    print(f"[WinRate] {len(df_buy)} buy records | {df_buy['alias'].nunique()} seats | "
          f"{len(unique_keys)} unique (stock, date) pairs to fetch")

    fetcher = StockDataFetcher()

    # Parallel price fetch
    print(f"[WinRate] Fetching price windows ({max_workers} threads)...")
    price_cache = {}
    tasks = [
        (fetcher, row['clean_code'], row['date'], row['cache_key'])
        for _, row in unique_keys.iterrows()
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_task, t): t[3] for t in tasks}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            done += 1
            if done % 10 == 0 or done == len(futures):
                print(f"  fetched {done}/{len(futures)}", end="\r")
            try:
                key, df_prices = future.result(timeout=20)
                price_cache[key] = df_prices
            except Exception:
                pass

    print(f"\n[WinRate] Price data fetched for {sum(v is not None for v in price_cache.values())} / {len(price_cache)} pairs.")

    # Calculate returns per record
    records = []
    for _, row in df_buy.iterrows():
        key = row['cache_key']
        df_prices = price_cache.get(key)
        returns = _calc_returns(df_prices)
        if not returns:
            continue
        records.append({
            'alias': row['alias'],
            'category': row.get('category', ''),
            'date': row['date'],
            'stock_code': row['clean_code'],
            'stock_name': row.get('stock_name', ''),
            'net_amt': row['net_amt'],
            't1_return': returns.get('t1'),
            't3_return': returns.get('t3'),
            't5_return': returns.get('t5'),
        })

    if not records:
        print("[WinRate] No return data could be calculated.")
        return None

    df_detail = pd.DataFrame(records)
    df_detail.to_csv(DETAIL_CSV, index=False, encoding='utf-8-sig')
    print(f"[WinRate] Detail saved → {DETAIL_CSV}")

    # Aggregate stats per alias
    stats = []
    for alias, grp in df_detail.groupby('alias'):
        row = {
            'alias': alias,
            'category': grp['category'].iloc[0],
            'appearances': len(grp),
        }
        for col, label in [('t1_return', 'T+1'), ('t3_return', 'T+3'), ('t5_return', 'T+5')]:
            valid = grp[col].dropna()
            n = len(valid)
            row[f'{label}_样本数'] = n
            if n > 0:
                row[f'{label}_胜率(%)'] = round((valid > 0).mean() * 100, 1)
                row[f'{label}_平均收益(%)'] = round(float(valid.mean()), 2)
            else:
                row[f'{label}_胜率(%)'] = None
                row[f'{label}_平均收益(%)'] = None
        stats.append(row)

    df_stats = pd.DataFrame(stats).sort_values('T+1_样本数', ascending=False).reset_index(drop=True)
    df_stats.to_csv(WINRATE_CSV, index=False, encoding='utf-8-sig')
    print(f"[WinRate] Stats saved → {WINRATE_CSV}")

    return df_stats, df_detail


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def generate_winrate_html(df_stats: pd.DataFrame, df_detail: pd.DataFrame):
    """Render an interactive HTML report and write to OUTPUT_DIR + share_reports."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---- summary table rows ----
    table_rows = ""
    for _, r in df_stats.iterrows():
        def _fmt_cell(label):
            wr = r.get(f'{label}_胜率(%)')
            avg = r.get(f'{label}_平均收益(%)')
            n = r.get(f'{label}_样本数', 0)
            if wr is None or n == 0:
                return '<td colspan="2" style="color:#aaa">数据不足</td>'
            wr_color = '#e74c3c' if wr >= 60 else ('#f39c12' if wr >= 50 else '#7f8c8d')
            avg_color = '#e74c3c' if avg > 0 else '#2ecc71'
            return (
                f'<td style="color:{wr_color};font-weight:bold">{wr}%'
                f'<br><span style="font-size:11px;color:#999">({n}次)</span></td>'
                f'<td style="color:{avg_color}">{avg:+.2f}%</td>'
            )

        cat = r.get('category', '')
        cat_badge = (
            f'<span style="background:#8e44ad;color:white;padding:2px 6px;'
            f'border-radius:3px;font-size:11px">{cat}</span>' if cat else ''
        )
        table_rows += f"""
        <tr>
            <td style="font-weight:bold">{r['alias']} {cat_badge}</td>
            <td>{int(r['appearances'])}</td>
            {_fmt_cell('T+1')}
            {_fmt_cell('T+3')}
            {_fmt_cell('T+5')}
        </tr>"""

    # ---- recent trades per alias (last 20) ----
    recent_trades_json = {}
    for alias, grp in df_detail.groupby('alias'):
        grp_sorted = grp.sort_values('date', ascending=False).head(20)
        trades = []
        for _, tr in grp_sorted.iterrows():
            trades.append({
                'date': tr['date'],
                'code': tr['stock_code'],
                'name': tr['stock_name'],
                'net': round(tr['net_amt'] / 10000, 0),
                't1': tr['t1_return'] if pd.notnull(tr.get('t1_return')) else None,
                't3': tr['t3_return'] if pd.notnull(tr.get('t3_return')) else None,
                't5': tr['t5_return'] if pd.notnull(tr.get('t5_return')) else None,
            })
        recent_trades_json[alias] = trades

    # ---- bar chart data: T+1 win rate for each seat ----
    chart_aliases = df_stats['alias'].tolist()
    chart_wr_t1 = [r if r is not None else 0 for r in df_stats['T+1_胜率(%)'].tolist()]
    chart_wr_t3 = [r if r is not None else 0 for r in df_stats['T+3_胜率(%)'].tolist()]

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>龙虎榜席位胜率分析 - {generated_at}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background: #f5f7fa; color: #333; }}
  .header {{ background: white; padding: 24px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,.06); margin-bottom: 20px; text-align: center; }}
  .header h1 {{ margin: 0 0 6px; font-size: 24px; }}
  .header p {{ margin: 0; color: #888; }}
  .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,.06); margin-bottom: 20px; }}
  h2 {{ color: #444; border-left: 5px solid #3498db; padding-left: 10px; margin-top: 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ border: 1px solid #eee; padding: 9px 12px; text-align: center; font-size: 13px; }}
  th {{ background: #f8f9fa; font-weight: bold; }}
  tr:hover {{ background: #fafbff; }}
  .chart-box {{ width: 100%; height: 420px; }}
  .detail-box {{ max-height: 340px; overflow-y: auto; margin-top: 14px; }}
  .detail-table th, .detail-table td {{ font-size: 12px; padding: 6px 10px; }}
  .up {{ color: #e74c3c; }} .down {{ color: #2ecc71; }}
  select {{ padding: 6px 10px; font-size: 14px; border-radius: 4px; border: 1px solid #ccc; min-width: 160px; }}
  .note {{ font-size: 12px; color: #999; margin-top: 6px; }}
</style>
</head>
<body>

<div class="header">
  <h1>龙虎榜席位胜率分析</h1>
  <p>生成时间: {generated_at} &nbsp;|&nbsp; 数据来源: 龙虎榜历史记录 + 历史价格</p>
  <p class="note">胜率 = 席位净买入后，该股在对应周期内上涨的比例 &nbsp;|&nbsp; 仅统计净买入记录</p>
</div>

<!-- 胜率总览图 -->
<div class="card">
  <h2>各席位 T+1 / T+3 胜率对比</h2>
  <div id="barChart" class="chart-box"></div>
</div>

<!-- 汇总表 -->
<div class="card">
  <h2>席位胜率汇总表</h2>
  <table>
    <thead>
      <tr>
        <th>席位 (别名)</th>
        <th>出现次数</th>
        <th>T+1 胜率</th><th>T+1 均收益</th>
        <th>T+3 胜率</th><th>T+3 均收益</th>
        <th>T+5 胜率</th><th>T+5 均收益</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
  <p class="note">胜率颜色: <span style="color:#e74c3c">■ ≥60%</span> &nbsp; <span style="color:#f39c12">■ 50-60%</span> &nbsp; <span style="color:#7f8c8d">■ &lt;50%</span></p>
</div>

<!-- 近期交易明细 -->
<div class="card">
  <h2>席位近期交易明细</h2>
  <div style="margin-bottom:12px">
    <label style="font-weight:bold;margin-right:8px">选择席位:</label>
    <select id="aliasSelect" onchange="showDetail()"></select>
  </div>
  <div class="detail-box">
    <table class="detail-table" id="detailTable">
      <thead>
        <tr>
          <th>日期</th><th>代码</th><th>名称</th>
          <th>净买入(万)</th><th>T+1</th><th>T+3</th><th>T+5</th>
        </tr>
      </thead>
      <tbody id="detailBody"></tbody>
    </table>
  </div>
</div>

<script>
var tradesData = {json.dumps(recent_trades_json, ensure_ascii=False)};
var aliases = {json.dumps(chart_aliases, ensure_ascii=False)};
var wr_t1   = {json.dumps(chart_wr_t1)};
var wr_t3   = {json.dumps(chart_wr_t3)};

// Bar chart
var chart = echarts.init(document.getElementById('barChart'));
chart.setOption({{
  tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
  legend: {{ data: ['T+1 胜率(%)', 'T+3 胜率(%)'] }},
  grid: {{ left: '3%', right: '4%', bottom: '10%', containLabel: true }},
  xAxis: {{ type: 'category', data: aliases, axisLabel: {{ rotate: 30, fontSize: 11 }} }},
  yAxis: {{ type: 'value', name: '胜率(%)', max: 100,
            markLine: {{ data: [{{ yAxis: 50, name: '50%基准线', lineStyle: {{ color: '#e74c3c', type: 'dashed' }} }}] }} }},
  series: [
    {{ name: 'T+1 胜率(%)', type: 'bar', data: wr_t1, itemStyle: {{ color: '#e74c3c' }},
       label: {{ show: true, position: 'top', formatter: '{{c}}%', fontSize: 11 }} }},
    {{ name: 'T+3 胜率(%)', type: 'bar', data: wr_t3, itemStyle: {{ color: '#3498db' }},
       label: {{ show: true, position: 'top', formatter: '{{c}}%', fontSize: 11 }} }}
  ]
}});

// Detail dropdown
var sel = document.getElementById('aliasSelect');
Object.keys(tradesData).forEach(function(a) {{
  var opt = document.createElement('option');
  opt.value = a; opt.innerText = a;
  sel.appendChild(opt);
}});

function showDetail() {{
  var alias = document.getElementById('aliasSelect').value;
  var trades = tradesData[alias] || [];
  var tbody = document.getElementById('detailBody');
  tbody.innerHTML = '';
  trades.forEach(function(t) {{
    function fmtR(v) {{
      if (v === null || v === undefined) return '<td style="color:#ccc">-</td>';
      var cls = v > 0 ? 'up' : 'down';
      return '<td class="' + cls + '">' + (v > 0 ? '+' : '') + v.toFixed(2) + '%</td>';
    }}
    tbody.innerHTML += '<tr>'
      + '<td>' + t.date + '</td>'
      + '<td>' + t.code + '</td>'
      + '<td>' + t.name + '</td>'
      + '<td>' + t.net.toFixed(0) + '</td>'
      + fmtR(t.t1) + fmtR(t.t3) + fmtR(t.t5)
      + '</tr>';
  }});
}}

if (Object.keys(tradesData).length > 0) showDetail();
window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body>
</html>"""

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[WinRate] HTML report → {REPORT_FILE}")

    shared_dir = os.path.dirname(SHARED_REPORT_FILE)
    os.makedirs(shared_dir, exist_ok=True)
    try:
        with open(SHARED_REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[WinRate] Shared report → {SHARED_REPORT_FILE}")
    except Exception as e:
        print(f"[WinRate] Could not write shared report: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = analyze_win_rates()
    if result:
        df_stats, df_detail = result
        generate_winrate_html(df_stats, df_detail)
        print("\n[WinRate] Done.")
        print(df_stats[['alias', 'appearances', 'T+1_胜率(%)', 'T+1_平均收益(%)',
                         'T+3_胜率(%)', 'T+3_平均收益(%)']].to_string(index=False))
    else:
        print("[WinRate] Analysis could not be completed.")
