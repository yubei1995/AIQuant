import os
import pandas as pd
import json
from datetime import datetime

def generate_daily_report(output_dir, date_str):
    # File paths
    margin_path = os.path.join(output_dir, "margin_data.csv")
    block_margin_path = os.path.join(output_dir, "block_margin.csv")
    foreign_path = os.path.join(output_dir, "foreign_flow.csv")
    lhb_path = os.path.join(output_dir, "lhb_data.csv")
    market_margin_path = os.path.join(output_dir, "market_margin_history.csv")
    index_turnover_path = os.path.join(output_dir, "index_turnover_history.csv")
    
    # Load Data
    df_margin = pd.read_csv(margin_path) if os.path.exists(margin_path) else pd.DataFrame()
    df_block_margin = pd.read_csv(block_margin_path) if os.path.exists(block_margin_path) else pd.DataFrame()
    df_foreign = pd.read_csv(foreign_path) if os.path.exists(foreign_path) else pd.DataFrame()
    df_lhb = pd.read_csv(lhb_path) if os.path.exists(lhb_path) else pd.DataFrame()
    df_market_margin = pd.read_csv(market_margin_path) if os.path.exists(market_margin_path) else pd.DataFrame()
    df_index_turnover = pd.read_csv(index_turnover_path) if os.path.exists(index_turnover_path) else pd.DataFrame()
    
    # Prepare Data for Charts
    
    # 0. Block Margin (Ranked)
    block_margin_data = {'names': [], 'values': []}
    block_margin_ratio_data = {'names': [], 'values': []} # New Ratio Data

    if not df_block_margin.empty:
        # Convert to Wan or Yi?
        # Use Yi (100 million)
        names = df_block_margin['block_name'].tolist()
        values = (df_block_margin['margin_net_buy_sum'] / 100000000).round(4).tolist()
        block_margin_data['names'] = names
        block_margin_data['values'] = values
        
        # Ratio
        if 'net_buy_ratio' in df_block_margin.columns:
            ratios = df_block_margin['net_buy_ratio'].round(2).tolist()
            block_margin_ratio_data['names'] = names
            block_margin_ratio_data['values'] = ratios
        else:
            block_margin_ratio_data['names'] = names
            block_margin_ratio_data['values'] = [0] * len(names)

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

    # 2.5 Market Margin Trend
    market_margin_trend = {'dates': [], 'total': []}
    if not df_market_margin.empty:
        df_market_margin = df_market_margin.sort_values('date')
        market_margin_trend['dates'] = df_market_margin['date'].astype(str).apply(lambda x: x[4:]).tolist() # MMDD
        # Convert to Yi
        market_margin_trend['total'] = (df_market_margin['total_balance'] / 100000000).round(2).tolist()

    # 3. Index Turnover History
    index_turnover_data = {'dates': [], 'series': []}
    if not df_index_turnover.empty:
        # Pivot or reorganize
        # Data: date, name, turnover_yi
        dates = sorted(df_index_turnover['date'].unique().tolist())
        index_turnover_data['dates'] = [str(d)[4:] for d in dates] # MMDD format
        
        # Series
        names = ["上证50", "沪深300", "中证500", "中证1000", "中证2000"]
        for name in names:
            # Filter for this index
            df_sub = df_index_turnover[df_index_turnover['name'] == name]
            # Create a dict mapping date -> value to handle missing dates if any
            val_map = {str(row['date']): row['turnover_yi'] for _, row in df_sub.iterrows()}
            
            # Align with dates list
            data_list = [val_map.get(str(d), 0) for d in dates]
            
            index_turnover_data['series'].append({
                'name': name,
                'data': data_list
            })

    # Rename columns for display
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
        
        <!-- 1. Index Turnover (Style & Liquidity) -->
        <div class="card">
            <h2>主要宽基指数成交额趋势 (市场风格监控)</h2>
            <div id="index_turnover_chart" class="chart-container"></div>
        </div>

        <!-- 2. Market Margin Trend -->
        <div class="card">
             <h2>全市场融资余额走势 (近10日)</h2>
             <div id="market_margin_chart" class="chart-container"></div>
        </div>

        <!-- 3. Block Margin -->
        <div class="card">
            <h2>板块融资净买入 (按板块强度排名)</h2>
            <div id="block_margin_chart" class="chart-container"></div>
            <h3 style="margin-top: 30px; color: #34495e;">板块融资异动占比 (净买入/昨日余额 %)</h3>
            <div id="block_margin_ratio_chart" class="chart-container"></div>
        </div>

        <!-- 4. Foreign Capital Flow -->
        <div class="card">
            <h2>外资/主力资金流向 (前10/后10)</h2>
            <div id="foreign_chart" class="chart-container"></div>
        </div>

        <!-- 5. Margin Trading (Ranked) -->
        <div class="card">
            <h2>融资余额排行 (前20)</h2>
            <div id="margin_chart" class="chart-container"></div>
        </div>

        <!-- 5. Dragon & Tiger List -->
        <div class="card">
            <h2>龙虎榜数据</h2>
            <div style="overflow-x: auto;">
                {df_lhb.to_html(classes='table', index=False, float_format=lambda x: '{:,.2f}'.format(x)) if not df_lhb.empty else '<p>监控股票今日无上榜数据</p>'}
            </div>
        </div>
    </div>

    <script>
        // --- Block Margin Chart ---
        var blockMarginChart = echarts.init(document.getElementById('block_margin_chart'));
        var blockMarginData = {json.dumps(block_margin_data)};
        
        var blockMarginOption = {{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: [
                {{ type: 'category', data: blockMarginData.names, axisLabel: {{ interval: 0, rotate: 45 }} }}
            ],
            yAxis: [
                {{ type: 'value', name: '净买入 (亿元)' }}
            ],
            series: [
                {{
                    name: '融资净买入',
                    type: 'bar',
                    data: blockMarginData.values,
                    itemStyle: {{ 
                        color: function(params) {{
                            return params.value >= 0 ? '#e74c3c' : '#27ae60';
                        }}
                    }}
                }}
            ]
        }};
        blockMarginChart.setOption(blockMarginOption);

        // --- Block Margin Ratio Chart ---
        var blockMarginRatioChart = echarts.init(document.getElementById('block_margin_ratio_chart'));
        var blockMarginRatioData = {json.dumps(block_margin_ratio_data)};
        
        var blockMarginRatioOption = {{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: [
                {{ type: 'category', data: blockMarginRatioData.names, axisLabel: {{ interval: 0, rotate: 45 }} }}
            ],
            yAxis: [
                {{ type: 'value', name: '变动比例 (%)' }}
            ],
            series: [
                {{
                    name: '净买入占比',
                    type: 'bar',
                    data: blockMarginRatioData.values,
                    itemStyle: {{ 
                        color: function(params) {{
                            return params.value >= 0 ? '#e74c3c' : '#27ae60';
                        }}
                    }}
                }}
            ]
        }};
        blockMarginRatioChart.setOption(blockMarginRatioOption);

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

        // --- Market Margin Trend Chart ---
        var marketMarginChart = echarts.init(document.getElementById('market_margin_chart'));
        var marketMarginData = {json.dumps(market_margin_trend)};
        
        var marketMarginOption = {{
            tooltip: {{ trigger: 'axis' }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{
                type: 'category',
                boundaryGap: false,
                data: marketMarginData.dates
            }},
            yAxis: {{
                type: 'value',
                name: '余额 (亿元)',
                scale: true // Auto scale min/max
            }},
            series: [
                {{
                    name: '市场融资总额',
                    type: 'line',
                    data: marketMarginData.total,
                    smooth: true,
                    areaStyle: {{
                         color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: 'rgba(52, 152, 219, 0.5)' }},
                            {{ offset: 1, color: 'rgba(52, 152, 219, 0.1)' }}
                          ])
                    }},
                    itemStyle: {{ color: '#2980b9' }}
                }}
            ]
        }};
        marketMarginChart.setOption(marketMarginOption);

        // --- Index Turnover Chart ---
        var indexTurnoverChart = echarts.init(document.getElementById('index_turnover_chart'));
        var indexTurnoverRaw = {json.dumps(index_turnover_data)};
        
        // Define colors for indices
        var indexColors = {{
            '上证50': '#d62728', 
            '沪深300': '#ff7f0e',
            '中证500': '#2ca02c',
            '中证1000': '#1f77b4',
            '中证2000': '#9467bd'
        }};

        var indexSeries = indexTurnoverRaw.series.map(function(item) {{
            return {{
                name: item.name,
                type: 'line',
                data: item.data,
                itemStyle: {{ color: indexColors[item.name] || 'gray' }},
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                label: {{
                    show: true,
                    position: 'top',
                    formatter: function(p) {{
                         // Only show for the last point to avoid clutter
                         if (p.dataIndex === indexTurnoverRaw.dates.length - 1) {{
                             return parseInt(p.value);
                         }}
                         return '';
                    }}
                }}
            }};
        }});

        var indexTurnoverOption = {{
            tooltip: {{ trigger: 'axis' }},
            legend: {{ data: ['上证50', '沪深300', '中证500', '中证1000', '中证2000'] }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{
                type: 'category',
                boundaryGap: false,
                data: indexTurnoverRaw.dates
            }},
            yAxis: {{
                type: 'value',
                name: '成交额 (亿元)'
            }},
            series: indexSeries
        }};
        indexTurnoverChart.setOption(indexTurnoverOption);

        window.addEventListener('resize', function() {{
            blockMarginChart.resize();
            blockMarginRatioChart.resize();
            foreignChart.resize();
            marginChart.resize();
            marketMarginChart.resize();
            indexTurnoverChart.resize();
        }});
    </script>
</body>
</html>
    """
    
    output_path = os.path.join(output_dir, "daily_report.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Report generated: {output_path}")

if __name__ == "__main__":
    generate_daily_report(os.path.join(os.path.dirname(__file__), "output"), datetime.now().strftime("%Y%m%d"))
