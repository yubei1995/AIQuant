"""
AIQuant 统一产品仪表盘

整合所有服务输出，生成单页 HTML 产品原型：
  - 今日交易信号（带评分）
  - 策略回测曲线 + 绩效指标
  - 板块强度排行
  - 席位胜率总览
  - 龙虎榜资金流向

输出：
  share_reports/dashboard.html
  service/Signal_Engine/output/dashboard.html
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(PROJECT_ROOT)

from signal_scorer   import score_today_signals
from backtest_engine import run_backtest

# ── 输出路径 ─────────────────────────────────────────────────────────────────
OUTPUT_DIR     = os.path.join(os.path.dirname(__file__), 'output')
SHARED_DIR     = os.path.join(PROJECT_ROOT, 'share_reports')
LHB_OUTPUT     = os.path.join(PROJECT_ROOT, 'service/LHB_Analyse/output')
BLOCK_OUTPUT   = os.path.join(PROJECT_ROOT, 'service/Block_Analyse/output')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)

ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"


# ── 数据加载辅助 ──────────────────────────────────────────────────────────────
def _csv(path, **kw):
    return pd.read_csv(path, **kw) if os.path.exists(path) else pd.DataFrame()

def _json(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


# ── 各区块 HTML 生成 ──────────────────────────────────────────────────────────

def _signal_table(df: pd.DataFrame) -> str:
    if df.empty:
        return '<p style="color:#aaa;text-align:center;padding:30px">今日暂无可评分信号（等待龙虎榜数据）</p>'
    rows = ''
    for _, r in df.head(15).iterrows():
        score = r['score']
        bar_w = int(score * 10)
        color = r.get('level_color', '#7f8c8d')
        rows += f"""
        <tr>
          <td>
            <div style="background:#eee;border-radius:4px;height:8px;width:100px">
              <div style="background:{color};width:{bar_w}px;height:8px;border-radius:4px"></div>
            </div>
            <span style="font-weight:bold;font-size:15px;color:{color}">{score}</span>
          </td>
          <td><span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:12px">{r['level']}</span></td>
          <td style="font-weight:bold">{r['alias']}</td>
          <td style="color:#666">{r['stock_code']} {r['stock_name']}</td>
          <td style="color:#e74c3c">{r['T+1_胜率']}</td>
          <td style="color:#3498db">{r['T+3_胜率']}</td>
          <td style="color:{'#e74c3c' if '+' in str(r['T+1_均收益']) else '#2ecc71'}">{r['T+1_均收益']}</td>
          <td style="color:#888">{int(r['净买入(万)']) if '净买入(万)' in r else int(r['net_amt']//10000)} 万</td>
          <td style="color:#aaa">{r['样本数']} 次</td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#f8f9fa">
          <th style="padding:10px;text-align:left">评分</th>
          <th>等级</th><th>席位</th><th>个股</th>
          <th>T+1胜率</th><th>T+3胜率</th><th>T+1均收益</th><th>净买入</th><th>样本</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def _backtest_section(metrics: dict, df_equity: pd.DataFrame) -> tuple[str, str]:
    """Returns (metrics_html, echarts_js)"""
    if not metrics:
        no_data = '<p style="color:#aaa;text-align:center;padding:40px">回测数据积累中，请运行历史数据回填后查看</p>'
        return no_data, ''

    tr = metrics['total_return']
    ar = metrics['annual_return']
    md = metrics['max_drawdown']
    sh = metrics['sharpe']
    wr = metrics['trade_win_rate']
    nt = metrics['n_trades']

    def _card(label, val, color):
        return f'<div style="flex:1;background:{color}10;border-left:4px solid {color};padding:14px 18px;border-radius:6px"><div style="font-size:22px;font-weight:bold;color:{color}">{val}</div><div style="color:#888;font-size:12px;margin-top:4px">{label}</div></div>'

    metric_html = f"""
    <div style="font-size:12px;color:#999;margin-bottom:12px">策略: {metrics.get('strategy','')}</div>
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
      {_card('年化收益', f'{ar:+.1f}%',   '#e74c3c')}
      {_card('总收益',   f'{tr:+.1f}%',   '#e67e22')}
      {_card('最大回撤', f'-{md:.1f}%',   '#3498db')}
      {_card('Sharpe',  f'{sh:.2f}',      '#9b59b6')}
      {_card('交易胜率', f'{wr:.1f}%',    '#27ae60')}
      {_card('交易次数', f'{nt} 笔',      '#7f8c8d')}
    </div>"""

    if df_equity is not None and not df_equity.empty:
        dates    = df_equity['date'].tolist()
        capitals = df_equity['capital'].tolist()
        bench    = [metrics['initial_capital']] * len(dates)  # flat benchmark
        js = f"""
        var chartBacktest = echarts.init(document.getElementById('backtestChart'));
        chartBacktest.setOption({{
          tooltip: {{ trigger: 'axis', formatter: function(p) {{
            return p[0].name + '<br/>' + p.map(function(s){{ return s.marker + s.seriesName + ': ¥' + (s.value/10000).toFixed(0) + '万'; }}).join('<br/>');
          }} }},
          legend: {{ data: ['策略净值', '基准(持有现金)'] }},
          grid: {{ left:'3%', right:'4%', bottom:'3%', containLabel:true }},
          xAxis: {{ type:'category', data:{json.dumps(dates)}, axisLabel:{{ rotate:30, fontSize:10 }} }},
          yAxis: {{ type:'value', axisLabel:{{ formatter: function(v){{ return '¥'+(v/10000).toFixed(0)+'万'; }} }} }},
          series: [
            {{ name:'策略净值', type:'line', data:{json.dumps(capitals)}, smooth:true,
               itemStyle:{{color:'#e74c3c'}}, areaStyle:{{opacity:0.1, color:'#e74c3c'}},
               lineStyle:{{width:2}} }},
            {{ name:'基准(持有现金)', type:'line', data:{json.dumps(bench)}, smooth:false,
               itemStyle:{{color:'#bdc3c7'}}, lineStyle:{{type:'dashed', width:1}} }}
          ]
        }});"""
        chart_div = '<div id="backtestChart" style="width:100%;height:320px"></div>'
    else:
        js = ''
        chart_div = ''

    return metric_html + chart_div, js


def _block_table(df: pd.DataFrame) -> str:
    if df.empty:
        return '<p style="color:#aaa;text-align:center;padding:20px">板块数据加载中...</p>'
    cols_needed = ['细分板块', '1d(%)', '3d(%)', '5d(%)', '总成交额(亿)']
    cols = [c for c in cols_needed if c in df.columns]
    df_show = df[cols].head(15)
    rows = ''
    for _, r in df_show.iterrows():
        v1d = r.get('1d(%)', 0)
        color = '#e74c3c' if float(v1d) > 0 else '#2ecc71'
        rows += f"<tr><td style='text-align:left;padding:8px 12px;font-weight:bold'>{r['细分板块']}</td>"
        for c in cols[1:]:
            val = r[c]
            try:
                fv = float(val)
                vc = '#e74c3c' if fv > 0 else '#2ecc71'
                rows += f"<td style='color:{vc}'>{fv:+.2f}{'%' if '%' in c else '亿'}</td>"
            except:
                rows += f"<td>{val}</td>"
        rows += "</tr>"
    return f"""<div style="max-height:340px;overflow-y:auto">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#f8f9fa">{(''.join(f'<th style="padding:10px">{c}</th>' for c in cols))}</tr></thead>
      <tbody>{rows}</tbody>
    </table></div>"""


def _winrate_mini(df: pd.DataFrame) -> str:
    if df.empty:
        return '<p style="color:#aaa;text-align:center;padding:20px">胜率数据积累中...</p>'
    rows = ''
    for _, r in df.head(10).iterrows():
        t1 = r.get('T+1_胜率(%)')
        try:
            t1f = float(t1)
            bar_color = '#e74c3c' if t1f >= 60 else ('#f39c12' if t1f >= 50 else '#95a5a6')
            bar_w = int(t1f)
            t1_str = f"{t1f:.1f}%"
        except:
            bar_color, bar_w, t1_str = '#ccc', 50, '积累中'
        rows += f"""
        <tr>
          <td style="font-weight:bold;padding:7px 12px">{r['alias']}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div style="background:#eee;border-radius:4px;height:6px;width:80px">
                <div style="background:{bar_color};width:{min(bar_w,100)}px;height:6px;border-radius:4px"></div>
              </div>
              <span style="color:{bar_color};font-weight:bold;font-size:13px">{t1_str}</span>
            </div>
          </td>
          <td style="color:#888">{int(r.get('T+1_样本数', 0))} 次</td>
        </tr>"""
    return f"""<table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#f8f9fa"><th style="padding:10px;text-align:left">席位</th><th>T+1 胜率</th><th>样本数</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def _lhb_summary(df_hist: pd.DataFrame) -> str:
    if df_hist.empty or len(df_hist) < 1:
        return '<p style="color:#aaa;text-align:center;padding:20px">龙虎榜历史数据加载中...</p>'
    row = df_hist.sort_values('date').iloc[-1]
    date = row.get('date', '')

    def _fmt(v):
        try: return f"{float(v)/1e8:+.2f} 亿"
        except: return '-'

    items = [
        ('网红游资', row.get('hot_money_net', 0), '#e74c3c'),
        ('高频量化', row.get('quant_net', 0),     '#3498db'),
        ('机构',     row.get('inst_net', 0),       '#f1c40f'),
        ('外资',     row.get('foreign_net', 0),    '#9b59b6'),
    ]
    cards = ''
    for label, val, color in items:
        try:
            fv = float(val)
            vc = '#e74c3c' if fv > 0 else '#2ecc71'
            txt = f"{fv/1e8:+.2f} 亿"
        except:
            vc, txt = '#aaa', '-'
        cards += f'<div style="flex:1;text-align:center;padding:12px;background:{color}10;border-radius:8px"><div style="font-size:18px;font-weight:bold;color:{vc}">{txt}</div><div style="color:#888;font-size:12px;margin-top:4px">{label}</div></div>'
    return f'<div style="font-size:12px;color:#999;margin-bottom:12px">最新日期: {date}</div><div style="display:flex;gap:10px;flex-wrap:wrap">{cards}</div>'


# ── 主函数 ────────────────────────────────────────────────────────────────────

def generate_dashboard():
    print("[Dashboard] 开始生成统一仪表盘...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y年%m月%d日")

    # ── 数据准备 ──
    print("[Dashboard] 评分今日信号...")
    df_signals = score_today_signals()

    print("[Dashboard] 运行回测引擎...")
    bt_result = run_backtest()
    bt_metrics = bt_result[0] if bt_result else {}
    bt_equity  = bt_result[1] if bt_result else pd.DataFrame()

    df_block = _csv(os.path.join(BLOCK_OUTPUT, 'block_statistics.csv'))
    df_wr    = _csv(os.path.join(LHB_OUTPUT,   'seat_winrate.csv'))
    df_lhb_hist = _csv(os.path.join(LHB_OUTPUT, 'lhb_analysis_history.csv'))

    # ── 渲染区块 ──
    signal_html         = _signal_table(df_signals)
    bt_html, bt_js      = _backtest_section(bt_metrics, bt_equity)
    block_html          = _block_table(df_block)
    wr_html             = _winrate_mini(df_wr)
    lhb_html            = _lhb_summary(df_lhb_hist)

    # 今日信号数量
    strong_cnt  = len(df_signals[df_signals['level'] == '强烈关注']) if not df_signals.empty else 0
    watch_cnt   = len(df_signals[df_signals['level'] == '关注'])     if not df_signals.empty else 0
    total_seats = len(df_wr) if not df_wr.empty else 0
    backtest_ar = f"{bt_metrics.get('annual_return', 0):+.1f}%" if bt_metrics else "积累中"
    backtest_md = f"{bt_metrics.get('max_drawdown', 0):.1f}%"   if bt_metrics else "-"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AIQuant · 交易决策仪表盘 · {today}</title>
<script src="{ECHARTS_CDN}"></script>
<style>
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Microsoft YaHei',sans-serif; background:#f0f2f5; color:#333; }}
  .topbar {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
             color:white; padding:20px 30px; display:flex; align-items:center; justify-content:space-between; }}
  .topbar h1 {{ font-size:22px; letter-spacing:2px; }}
  .topbar .meta {{ font-size:12px; opacity:.7; text-align:right; }}
  .kpi-bar {{ display:flex; gap:0; background:white; border-bottom:1px solid #eee; }}
  .kpi {{ flex:1; padding:16px 24px; border-right:1px solid #eee; text-align:center; }}
  .kpi .val {{ font-size:24px; font-weight:bold; }}
  .kpi .lbl {{ font-size:11px; color:#999; margin-top:4px; }}
  .layout {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; padding:16px; }}
  .card {{ background:white; border-radius:10px; box-shadow:0 1px 4px rgba(0,0,0,.08); padding:20px; }}
  .card.full {{ grid-column:1/-1; }}
  h2 {{ font-size:14px; color:#444; font-weight:bold; margin-bottom:14px;
        border-left:4px solid #3498db; padding-left:10px; }}
  table th,table td {{ border:1px solid #f0f0f0; padding:8px 10px; text-align:center; }}
  table th {{ background:#fafafa; font-size:12px; }}
  .nav-links {{ display:flex; gap:10px; padding:12px 16px; background:white; border-top:1px solid #eee; flex-wrap:wrap; }}
  .nav-links a {{ text-decoration:none; color:#3498db; font-size:12px; padding:4px 10px; border:1px solid #3498db; border-radius:12px; }}
  .nav-links a:hover {{ background:#3498db; color:white; }}
  @media(max-width:768px){{ .layout{{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>

<!-- 顶栏 -->
<div class="topbar">
  <div>
    <h1>AIQuant &nbsp;·&nbsp; 交易决策仪表盘</h1>
    <div style="font-size:12px;opacity:.6;margin-top:4px">用历史数据告诉你，哪些资金行为值得下注</div>
  </div>
  <div class="meta">
    <div>{today}</div>
    <div>生成时间: {now}</div>
  </div>
</div>

<!-- KPI 条 -->
<div class="kpi-bar">
  <div class="kpi">
    <div class="val" style="color:#c0392b">{strong_cnt}</div>
    <div class="lbl">强烈关注信号</div>
  </div>
  <div class="kpi">
    <div class="val" style="color:#e67e22">{watch_cnt}</div>
    <div class="lbl">关注信号</div>
  </div>
  <div class="kpi">
    <div class="val" style="color:{'#27ae60' if '+' in str(backtest_ar) else '#e74c3c'}">{backtest_ar}</div>
    <div class="lbl">策略年化收益</div>
  </div>
  <div class="kpi">
    <div class="val" style="color:#3498db">{backtest_md}</div>
    <div class="lbl">最大回撤</div>
  </div>
  <div class="kpi">
    <div class="val" style="color:#9b59b6">{total_seats}</div>
    <div class="lbl">跟踪席位数</div>
  </div>
</div>

<!-- 主布局 -->
<div class="layout">

  <!-- 今日信号 -->
  <div class="card full">
    <h2>今日交易信号 &nbsp;<span style="font-size:11px;color:#999;font-weight:normal">评分 ≥ 8 = 强烈关注 | 6-8 = 关注 | &lt;6 = 观望</span></h2>
    {signal_html}
  </div>

  <!-- 回测 -->
  <div class="card full">
    <h2>席位跟随策略 · 历史回测</h2>
    {bt_html}
  </div>

  <!-- 板块 -->
  <div class="card">
    <h2>板块强度排行（今日）</h2>
    {block_html}
  </div>

  <!-- 席位胜率 -->
  <div class="card">
    <h2>席位历史胜率 Top 10</h2>
    {wr_html}
  </div>

  <!-- 龙虎榜资金 -->
  <div class="card full">
    <h2>龙虎榜资金流向（最新）</h2>
    {lhb_html}
  </div>

</div>

<!-- 详情报告链接 -->
<div class="nav-links">
  <span style="font-size:12px;color:#999;align-self:center">详细报告：</span>
  <a href="lhb_analysis_report.html">龙虎榜资金画像</a>
  <a href="seat_winrate_report.html">席位胜率详情</a>
  <a href="global_analysis_report.html">板块分析</a>
  <a href="daily_monitor_report.html">日监控</a>
</div>

<script>
{bt_js}
window.addEventListener('resize', function() {{
  ['backtestChart'].forEach(function(id) {{
    var el = document.getElementById(id);
    if (el) echarts.getInstanceByDom(el) && echarts.getInstanceByDom(el).resize();
  }});
}});
</script>
</body>
</html>"""

    # ── 写出 ──
    local_path  = os.path.join(OUTPUT_DIR, 'dashboard.html')
    shared_path = os.path.join(SHARED_DIR, 'dashboard.html')

    with open(local_path,  'w', encoding='utf-8') as f: f.write(html)
    with open(shared_path, 'w', encoding='utf-8') as f: f.write(html)

    print(f"[Dashboard] 仪表盘生成完成 → {shared_path}")
    return shared_path


if __name__ == '__main__':
    generate_dashboard()
