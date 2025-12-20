import os
import pandas as pd
import json
from datetime import datetime

def generate_daily_report(date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
        
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    
    # File paths
    margin_path = os.path.join(output_dir, f"margin_data_{date_str}.csv")
    foreign_path = os.path.join(output_dir, f"foreign_flow_{date_str}.csv")
    lhb_path = os.path.join(output_dir, f"lhb_data_{date_str}.csv")
    etf_path = os.path.join(output_dir, f"etf_shares_{date_str}.csv")
    
    # Load Data
    df_margin = pd.read_csv(margin_path) if os.path.exists(margin_path) else pd.DataFrame()
    df_foreign = pd.read_csv(foreign_path) if os.path.exists(foreign_path) else pd.DataFrame()
    df_lhb = pd.read_csv(lhb_path) if os.path.exists(lhb_path) else pd.DataFrame()
    df_etf = pd.read_csv(etf_path) if os.path.exists(etf_path) else pd.DataFrame()
    
    # Prepare Data for Charts
    
    # 1. Foreign Flow (Top 20 Inflow & Outflow)
    foreign_chart_data = {'names': [], 'values': []}
    if not df_foreign.empty:
        # Sort by net_inflow
        df_sorted = df_foreign.sort_values('net_inflow', ascending=False)
        # Top 10 and Bottom 10
        top10 = df_sorted.head(10)
        bottom10 = df_sorted.tail(10).sort_values('net_inflow', ascending=False) # Keep desc order for display
        
        combined = pd.concat([top10, bottom10])
        foreign_chart_data['names'] = combined['name'].tolist()
        foreign_chart_data['values'] = combined['net_inflow'].tolist()
        
    # 2. Margin (Top 20 Balance)
    margin_chart_data = {'names': [], 'values': []}
    if not df_margin.empty:
        df_sorted = df_margin.sort_values('margin_balance', ascending=False).head(20)
        margin_chart_data['names'] = df_sorted['name'].tolist()
        margin_chart_data['values'] = df_sorted['margin_balance'].tolist()

    # 3. ETF Shares
    etf_chart_data = {'names': [], 'shares': [], 'turnover': []}
    if not df_etf.empty:
        etf_chart_data['names'] = df_etf['name'].tolist()
        etf_chart_data['shares'] = df_etf['current_shares'].tolist()
        etf_chart_data['turnover'] = df_etf['turnover'].tolist()

    # Rename columns for display
    if not df_etf.empty:
        df_etf = df_etf.rename(columns={
            'code': '代码', 'name': '名称', 'current_shares': '当前份额', 
            'price': '最新价', 'turnover': '成交额'
        })
        
    if not df_lhb.empty:
        df_lhb = df_lhb.rename(columns={
            'code': '代码', 'name': '名称', 'reason': '上榜原因', 
            'close': '收盘价', 'pct_change': '涨跌幅', 'net_buy': '净买入额'
        })

    # HTML Template
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>每日市场监控日报 - {date_str}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{ font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif; margin: 0; padding: 20px; background-color: #f5f7fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; padding: 20px; }}
        h1 {{ color: #2c3e50; margin-bottom: 30px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 0; }}
        .chart-container {{ height: 400px; width: 100%; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; color: #666; font-weight: 600; }}
        tr:hover {{ background-color: #f1f1f1; }}
        .positive {{ color: #e74c3c; }}
        .negative {{ color: #27ae60; }}
        .tag {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 12px; background: #eee; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>每日市场监控日报 <small style="font-size: 0.5em; color: #7f8c8d;">{date_str}</small></h1>
        
        <!-- 1. Foreign Capital Flow -->
        <div class="card">
            <h2>外资/主力资金流向 (前10/后10)</h2>
            <div id="foreign_chart" class="chart-container"></div>
        </div>

        <!-- 2. Margin Trading -->
        <div class="card">
            <h2>融资余额排行 (前20)</h2>
            <div id="margin_chart" class="chart-container"></div>
        </div>

        <!-- 3. ETF Shares -->
        <div class="card">
            <h2>国家队宽基ETF份额监控</h2>
            <div id="etf_chart" class="chart-container"></div>
            <div style="margin-top: 20px; overflow-x: auto;">
                {df_etf.to_html(classes='table', index=False, float_format=lambda x: '{:,.0f}'.format(x)) if not df_etf.empty else '<p>暂无ETF数据</p>'}
            </div>
        </div>

        <!-- 4. Dragon & Tiger List -->
        <div class="card">
            <h2>龙虎榜数据</h2>
            <div style="overflow-x: auto;">
                {df_lhb.to_html(classes='table', index=False, float_format=lambda x: '{:,.2f}'.format(x)) if not df_lhb.empty else '<p>监控股票今日无上榜数据</p>'}
            </div>
        </div>
    </div>

    <script>
        // --- Foreign Flow Chart ---
        var foreignChart = echarts.init(document.getElementById('foreign_chart'));
        var foreignData = {json.dumps(foreign_chart_data)};
        
        var foreignOption = {{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: [
                {{ type: 'category', data: foreignData.names, axisLabel: {{ interval: 0, rotate: 45 }} }}
            ],
            yAxis: [
                {{ type: 'value', name: '净流入额 (元)' }}
            ],
            series: [
                {{
                    name: '净流入',
                    type: 'bar',
                    data: foreignData.values,
                    itemStyle: {{
                        color: function(params) {{
                            return params.value >= 0 ? '#e74c3c' : '#27ae60';
                        }}
                    }}
                }}
            ]
        }};
        foreignChart.setOption(foreignOption);

        // --- Margin Chart ---
        var marginChart = echarts.init(document.getElementById('margin_chart'));
        var marginData = {json.dumps(margin_chart_data)};
        
        var marginOption = {{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: [
                {{ type: 'category', data: marginData.names, axisLabel: {{ interval: 0, rotate: 45 }} }}
            ],
            yAxis: [
                {{ type: 'value', name: '余额 (元)' }}
            ],
            series: [
                {{
                    name: '融资余额',
                    type: 'bar',
                    data: marginData.values,
                    itemStyle: {{ color: '#3498db' }}
                }}
            ]
        }};
        marginChart.setOption(marginOption);

        // --- ETF Chart ---
        var etfChart = echarts.init(document.getElementById('etf_chart'));
        var etfData = {json.dumps(etf_chart_data)};
        
        var etfOption = {{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
            legend: {{ data: ['份额', '成交额'] }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: [
                {{ type: 'category', data: etfData.names, axisLabel: {{ interval: 0 }} }}
            ],
            yAxis: [
                {{ type: 'value', name: '份额', position: 'left' }},
                {{ type: 'value', name: '成交额', position: 'right', splitLine: {{ show: false }} }}
            ],
            series: [
                {{
                    name: '份额',
                    type: 'bar',
                    data: etfData.shares,
                    itemStyle: {{ color: '#f39c12' }}
                }},
                {{
                    name: '成交额',
                    type: 'line',
                    yAxisIndex: 1,
                    data: etfData.turnover,
                    itemStyle: {{ color: '#8e44ad' }}
                }}
            ]
        }};
        etfChart.setOption(etfOption);

        window.addEventListener('resize', function() {{
            foreignChart.resize();
            marginChart.resize();
            etfChart.resize();
        }});
    </script>
</body>
</html>
    """
    
    output_path = os.path.join(output_dir, f"daily_report_{date_str}.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Report generated: {output_path}")

if __name__ == "__main__":
    generate_daily_report()
