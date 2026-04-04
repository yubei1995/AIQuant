"""
AIQuant 统一产品仪表盘

核心理念：每天只给 3 个判断，每个判断有据可查。

结构：
  [英雄区] 今日 Top 3 信号判断书（卡片式，有结论）
  [支撑区] 回测绩效 | 板块强度 | 席位胜率 | 资金流向

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

OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), 'output')
SHARED_DIR   = os.path.join(PROJECT_ROOT, 'share_reports')
LHB_OUTPUT   = os.path.join(PROJECT_ROOT, 'service/LHB_Analyse/output')
BLOCK_OUTPUT = os.path.join(PROJECT_ROOT, 'service/Block_Analyse/output')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)

ECHARTS = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"


def _csv(path):
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()


# ── 判断书卡片（英雄区）──────────────────────────────────────────────────────

def _verdict_cards(df: pd.DataFrame) -> str:
    if df.empty:
        return '''
        <div style="text-align:center;padding:60px 20px;color:#aaa">
          <div style="font-size:48px;margin-bottom:16px">📊</div>
          <div style="font-size:16px;font-weight:bold;margin-bottom:8px">今日信号数据积累中</div>
          <div style="font-size:13px">请先运行龙虎榜分析或等待每日自动更新</div>
        </div>'''

    # 只取评分最高的前 3 个
    top3 = df.head(3)
    cards = ''
    for rank, (_, r) in enumerate(top3.iterrows(), 1):
        vc    = r['verdict_color']
        stock = f"{r['stock_code']} {r['stock_name']}" if r['stock_name'] else r['stock_code']
        score_bar = int(r['score'] * 10)

        cards += f'''
        <div style="flex:1;min-width:280px;background:white;border-radius:12px;
                    box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden;
                    border-top:4px solid {vc}">
          <!-- 卡片头 -->
          <div style="padding:18px 20px 12px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
              <span style="background:{vc}20;color:{vc};font-weight:bold;font-size:12px;
                           padding:3px 10px;border-radius:20px">
                #{rank} &nbsp;{r["alias"]}
              </span>
              <span style="font-size:22px;font-weight:bold;color:{vc}">{r["score"]}</span>
            </div>
            <div style="font-size:16px;font-weight:bold;color:#222;margin-bottom:6px">{stock}</div>
            <div style="font-size:12px;color:#666;line-height:1.6">{r["why"]}</div>
          </div>

          <!-- 胜率数据 -->
          <div style="display:flex;border-top:1px solid #f0f0f0;border-bottom:1px solid #f0f0f0">
            <div style="flex:1;padding:10px;text-align:center;border-right:1px solid #f0f0f0">
              <div style="font-size:18px;font-weight:bold;color:{vc}">{r["T+1_胜率"]}</div>
              <div style="font-size:11px;color:#999">T+1 胜率</div>
            </div>
            <div style="flex:1;padding:10px;text-align:center;border-right:1px solid #f0f0f0">
              <div style="font-size:18px;font-weight:bold;color:#3498db">{r["T+3_胜率"]}</div>
              <div style="font-size:11px;color:#999">T+3 胜率</div>
            </div>
            <div style="flex:1;padding:10px;text-align:center">
              <div style="font-size:18px;font-weight:bold;color:#9b59b6">{r["样本数"]} 次</div>
              <div style="font-size:11px;color:#999">历史样本</div>
            </div>
          </div>

          <!-- 风险提示 -->
          <div style="padding:10px 20px;background:#fafafa">
            <div style="font-size:11px;color:#e67e22">⚠ {r["risk_note"]}</div>
          </div>

          <!-- 结论 -->
          <div style="padding:14px 20px;display:flex;align-items:center;justify-content:space-between">
            <div>
              <div style="font-size:20px;font-weight:bold;color:{vc}">
                {r["verdict_icon"]} {r["verdict"]}
              </div>
              <div style="font-size:12px;color:#888;margin-top:2px">{r["position_hint"]}</div>
            </div>
            <!-- 评分进度条 -->
            <div style="text-align:right">
              <div style="background:#eee;border-radius:4px;height:6px;width:80px">
                <div style="background:{vc};width:{score_bar}px;height:6px;border-radius:4px"></div>
              </div>
              <div style="font-size:10px;color:#ccc;margin-top:2px">综合评分</div>
            </div>
          </div>
        </div>'''

    return f'<div style="display:flex;gap:16px;flex-wrap:wrap">{cards}</div>'


# ── 回测区块 ─────────────────────────────────────────────────────────────────

def _backtest_block(metrics: dict, df_eq: pd.DataFrame) -> tuple[str, str]:
    if not metrics:
        placeholder = '<div style="text-align:center;padding:40px;color:#aaa">回测数据积累中，运行历史回填后自动生成</div>'
        return placeholder, ''

    def _kpi(label, val, color):
        return (f'<div style="flex:1;min-width:100px;background:{color}10;border-left:3px solid {color};'
                f'padding:12px 16px;border-radius:6px">'
                f'<div style="font-size:20px;font-weight:bold;color:{color}">{val}</div>'
                f'<div style="font-size:11px;color:#999;margin-top:2px">{label}</div></div>')

    ar = metrics['annual_return']
    md = metrics['max_drawdown']
    sh = metrics['sharpe']
    wr = metrics['trade_win_rate']
    nt = metrics['n_trades']
    ar_color = '#e74c3c' if ar >= 0 else '#2ecc71'

    kpis = (
        _kpi('年化收益', f'{ar:+.1f}%', ar_color) +
        _kpi('最大回撤', f'-{md:.1f}%', '#3498db') +
        _kpi('Sharpe',   f'{sh:.2f}',   '#9b59b6') +
        _kpi('交易胜率', f'{wr:.1f}%',  '#27ae60') +
        _kpi('交易笔数', f'{nt}',        '#7f8c8d')
    )

    strat = metrics.get('strategy', '')
    html  = (f'<div style="font-size:11px;color:#aaa;margin-bottom:12px">策略: {strat}</div>'
             f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px">{kpis}</div>'
             f'<div id="btChart" style="width:100%;height:260px"></div>')

    dates = df_eq['date'].tolist() if not df_eq.empty else []
    caps  = df_eq['capital'].tolist() if not df_eq.empty else []
    bench = [metrics['initial_capital']] * len(dates)

    js = f"""
    var btChart = echarts.init(document.getElementById('btChart'));
    btChart.setOption({{
      tooltip:{{ trigger:'axis', formatter:function(p){{
        return p[0].name+'<br/>'+p.map(function(s){{
          return s.marker+s.seriesName+': ¥'+(s.value/10000).toFixed(0)+'万';
        }}).join('<br/>');
      }} }},
      legend:{{ data:['策略净值','持有现金'] }},
      grid:{{ left:'3%',right:'4%',bottom:'3%',containLabel:true }},
      xAxis:{{ type:'category', data:{json.dumps(dates)}, axisLabel:{{rotate:30,fontSize:10}} }},
      yAxis:{{ type:'value', axisLabel:{{ formatter:function(v){{return '¥'+(v/10000).toFixed(0)+'万';}} }} }},
      series:[
        {{ name:'策略净值', type:'line', data:{json.dumps(caps)}, smooth:true,
           itemStyle:{{color:'#e74c3c'}}, areaStyle:{{opacity:0.08,color:'#e74c3c'}}, lineStyle:{{width:2}} }},
        {{ name:'持有现金', type:'line', data:{json.dumps(bench)}, smooth:false,
           itemStyle:{{color:'#bdc3c7'}}, lineStyle:{{type:'dashed',width:1}} }}
      ]
    }});"""
    return html, js


# ── 简版板块 & 席位 & 资金流 ─────────────────────────────────────────────────

def _block_mini(df: pd.DataFrame) -> str:
    if df.empty:
        return '<div style="color:#aaa;text-align:center;padding:20px;font-size:13px">板块数据加载中...</div>'
    cols = [c for c in ['细分板块','1d(%)','3d(%)','5d(%)','总成交额(亿)'] if c in df.columns]
    rows = ''
    for _, r in df.head(10).iterrows():
        v1d = r.get('1d(%)', 0)
        try: c1d = '#e74c3c' if float(v1d) > 0 else '#2ecc71'
        except: c1d = '#999'
        cells = f'<td style="text-align:left;padding:7px 10px;font-weight:bold">{r["细分板块"]}</td>'
        for col in cols[1:]:
            try:
                fv = float(r[col])
                fc = '#e74c3c' if fv > 0 else '#2ecc71'
                cells += f'<td style="color:{fc}">{fv:+.2f}{"%" if "%" in col else "亿"}</td>'
            except:
                cells += f'<td>{r[col]}</td>'
        rows += f'<tr>{cells}</tr>'
    hdr = ''.join(f'<th style="padding:8px 10px">{c}</th>' for c in cols)
    return (f'<div style="max-height:300px;overflow-y:auto">'
            f'<table style="width:100%;border-collapse:collapse;font-size:12px">'
            f'<thead><tr style="background:#fafafa">{hdr}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def _wr_mini(df: pd.DataFrame) -> str:
    if df.empty:
        return '<div style="color:#aaa;text-align:center;padding:20px;font-size:13px">胜率数据积累中...</div>'
    rows = ''
    for _, r in df.head(8).iterrows():
        try:
            wr = float(r.get('T+1_胜率(%)'))
            wc = '#e74c3c' if wr >= 60 else ('#f39c12' if wr >= 50 else '#95a5a6')
            ws = f'{wr:.1f}%'
            bw = min(int(wr), 100)
        except:
            wc, ws, bw = '#ccc', '积累中', 50
        n = int(r.get('T+1_样本数', 0))
        rows += (f'<tr>'
                 f'<td style="font-weight:bold;padding:7px 10px;text-align:left">{r["alias"]}</td>'
                 f'<td><div style="display:flex;align-items:center;gap:6px">'
                 f'<div style="background:#eee;border-radius:3px;height:5px;width:70px">'
                 f'<div style="background:{wc};width:{bw}%;height:5px;border-radius:3px"></div></div>'
                 f'<span style="color:{wc};font-weight:bold;font-size:12px">{ws}</span></div></td>'
                 f'<td style="color:#aaa;font-size:12px">{n}次</td></tr>')
    return (f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
            f'<thead><tr style="background:#fafafa">'
            f'<th style="padding:8px 10px;text-align:left">席位</th>'
            f'<th>T+1 胜率</th><th>样本</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def _lhb_flow(df: pd.DataFrame) -> str:
    if df.empty:
        return '<div style="color:#aaa;text-align:center;padding:20px;font-size:13px">龙虎榜数据加载中...</div>'
    r   = df.sort_values('date').iloc[-1]
    dt  = r.get('date', '')
    items = [('网红游资', r.get('hot_money_net',0), '#e74c3c'),
             ('高频量化', r.get('quant_net',0),     '#3498db'),
             ('机构',     r.get('inst_net',0),       '#f1c40f'),
             ('外资',     r.get('foreign_net',0),    '#9b59b6')]
    cards = ''
    for lbl, val, color in items:
        try:
            fv = float(val); vc = '#e74c3c' if fv > 0 else '#2ecc71'
            txt = f'{fv/1e8:+.2f}亿'
        except:
            vc = txt = '#aaa', '-'
        cards += (f'<div style="flex:1;text-align:center;padding:12px 8px;'
                  f'background:{color}10;border-radius:8px">'
                  f'<div style="font-size:17px;font-weight:bold;color:{vc}">{txt}</div>'
                  f'<div style="font-size:11px;color:#999;margin-top:3px">{lbl}</div></div>')
    return (f'<div style="font-size:11px;color:#bbb;margin-bottom:10px">最新: {dt}</div>'
            f'<div style="display:flex;gap:8px;flex-wrap:wrap">{cards}</div>')


# ── 主函数 ───────────────────────────────────────────────────────────────────

def generate_dashboard():
    print("[Dashboard] 生成判断书仪表盘...")
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y年%m月%d日")

    df_signals = score_today_signals()
    bt_result  = run_backtest()
    bt_metrics = bt_result[0] if bt_result else {}
    bt_eq      = bt_result[1] if bt_result else pd.DataFrame()

    df_block    = _csv(os.path.join(BLOCK_OUTPUT, 'block_statistics.csv'))
    df_wr       = _csv(os.path.join(LHB_OUTPUT,   'seat_winrate.csv'))
    df_lhb_hist = _csv(os.path.join(LHB_OUTPUT,   'lhb_analysis_history.csv'))

    cards_html      = _verdict_cards(df_signals)
    bt_html, bt_js  = _backtest_block(bt_metrics, bt_eq)
    block_html      = _block_mini(df_block)
    wr_html         = _wr_mini(df_wr)
    lhb_html        = _lhb_flow(df_lhb_hist)

    # KPI 摘要
    strong  = len(df_signals[df_signals['verdict'] == '值得参与'])   if not df_signals.empty else 0
    caution = len(df_signals[df_signals['verdict'] == '谨慎参与'])   if not df_signals.empty else 0
    skip    = len(df_signals[df_signals['verdict'] == '本次观望'])    if not df_signals.empty else 0
    ar_txt  = f"{bt_metrics['annual_return']:+.1f}%" if bt_metrics else '积累中'
    ar_col  = ('#e74c3c' if bt_metrics and bt_metrics['annual_return'] >= 0 else '#2ecc71') if bt_metrics else '#aaa'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AIQuant · 每日判断书 · {today}</title>
<script src="{ECHARTS}"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Microsoft YaHei',sans-serif;background:#f0f2f5;color:#333}}
  .topbar{{background:linear-gradient(135deg,#1a1a2e,#0f3460);color:white;
           padding:18px 28px;display:flex;align-items:center;justify-content:space-between}}
  .topbar h1{{font-size:20px;letter-spacing:1px}}
  .topbar .sub{{font-size:11px;opacity:.6;margin-top:3px}}
  .topbar .meta{{font-size:11px;opacity:.6;text-align:right}}
  .kpi-row{{display:flex;background:white;border-bottom:1px solid #eee}}
  .kpi{{flex:1;padding:14px 20px;text-align:center;border-right:1px solid #eee}}
  .kpi .v{{font-size:22px;font-weight:bold}}
  .kpi .l{{font-size:11px;color:#999;margin-top:3px}}
  .wrap{{padding:16px;display:flex;flex-direction:column;gap:16px}}
  .card{{background:white;border-radius:10px;box-shadow:0 1px 6px rgba(0,0,0,.07);padding:20px}}
  h2{{font-size:14px;color:#444;font-weight:bold;margin-bottom:16px;
      border-left:4px solid #3498db;padding-left:10px}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  .nav{{display:flex;gap:8px;padding:12px 16px;background:white;
        border-top:1px solid #eee;flex-wrap:wrap;align-items:center}}
  .nav a{{text-decoration:none;color:#3498db;font-size:12px;padding:3px 10px;
          border:1px solid #3498db;border-radius:12px}}
  .nav a:hover{{background:#3498db;color:white}}
  @media(max-width:720px){{.two-col{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <h1>AIQuant &nbsp;·&nbsp; 每日判断书</h1>
    <div class="sub">数据不值钱，判断才值钱</div>
  </div>
  <div class="meta">{today}<br>更新: {now}</div>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="v" style="color:#27ae60">{strong}</div><div class="l">✅ 值得参与</div></div>
  <div class="kpi"><div class="v" style="color:#e67e22">{caution}</div><div class="l">⚠️ 谨慎参与</div></div>
  <div class="kpi"><div class="v" style="color:#95a5a6">{skip}</div><div class="l">⛔ 本次观望</div></div>
  <div class="kpi"><div class="v" style="color:{ar_col}">{ar_txt}</div><div class="l">策略年化收益</div></div>
</div>

<div class="wrap">

  <!-- ① 判断书（英雄区）-->
  <div class="card">
    <h2>今日信号判断 &nbsp;<span style="font-size:11px;color:#999;font-weight:normal">
      仅展示评分最高的 3 个，其余信号均不建议参与
    </span></h2>
    {cards_html}
  </div>

  <!-- ② 策略回测 -->
  <div class="card">
    <h2>席位跟随策略 · 历史回测</h2>
    {bt_html}
  </div>

  <!-- ③ 支撑数据 -->
  <div class="two-col">
    <div class="card">
      <h2>板块强度排行</h2>
      {block_html}
    </div>
    <div class="card">
      <h2>席位历史胜率</h2>
      {wr_html}
    </div>
  </div>

  <!-- ④ 龙虎榜资金 -->
  <div class="card">
    <h2>龙虎榜资金流向</h2>
    {lhb_html}
  </div>

</div>

<div class="nav">
  <span style="font-size:12px;color:#aaa">详情：</span>
  <a href="lhb_analysis_report.html">龙虎榜画像</a>
  <a href="seat_winrate_report.html">席位胜率</a>
  <a href="global_analysis_report.html">板块分析</a>
  <a href="daily_monitor_report.html">日监控</a>
</div>

<script>
{bt_js}
window.addEventListener('resize',function(){{
  var el=document.getElementById('btChart');
  if(el && echarts.getInstanceByDom(el)) echarts.getInstanceByDom(el).resize();
}});
</script>
</body>
</html>"""

    for path in [os.path.join(OUTPUT_DIR, 'dashboard.html'),
                 os.path.join(SHARED_DIR,  'dashboard.html')]:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)

    print(f"[Dashboard] 完成 → {os.path.join(SHARED_DIR, 'dashboard.html')}")
    return os.path.join(SHARED_DIR, 'dashboard.html')


if __name__ == '__main__':
    generate_dashboard()
