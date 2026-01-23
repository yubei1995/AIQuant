import pandas as pd
import os
import sys
import json
import xml.etree.ElementTree as ET

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
HISTORY_FILE = os.path.join(OUTPUT_DIR, 'lhb_analysis_history.csv')
REPORT_FILE = os.path.join(OUTPUT_DIR, 'lhb_analysis_report.html')
SHARED_REPORT_FILE = os.path.join(os.path.dirname(__file__), '../../share_reports/lhb_analysis_report.html')

def generate_html(df):
    # Sort by date
    df = df.sort_values('date')
    dates = df['date'].astype(str).tolist()
    
    # Data Series
    hot_money = df['hot_money_net'].tolist()
    quant = df['quant_net'].tolist()
    inst = df['inst_net'].tolist()
    foreign = df['foreign_net'].tolist()
    
    lhb_turnover = df['total_lhb_turnover'].tolist()
    market_turnover = df['total_market_turnover'].tolist()
    
    # Calculate Ratio (avoid div by zero)
    lhb_ratio = []
    for l, m in zip(lhb_turnover, market_turnover):
        if m > 0:
            lhb_ratio.append(round((l / m) * 100, 2))
        else:
            lhb_ratio.append(0)

    # Prepare Alias Data for Dropdown
    alias_history_file = os.path.join(OUTPUT_DIR, 'lhb_alias_history.csv')
    config_path = os.path.join(os.path.dirname(__file__), '../../data/lhb_config.xml')
    
    # 1. Get all configured aliases from XML
    all_configured_aliases = set()
    try:
        if os.path.exists(config_path):
            tree = ET.parse(config_path)
            root = tree.getroot()
            seat_mappings = root.find('SeatMappings')
            if seat_mappings:
                for category in seat_mappings.findall('Category'):
                    for alias in category.findall('Alias'):
                        name = alias.get('name')
                        if name:
                            all_configured_aliases.add(name)
    except Exception as e:
        print(f"Error parsing XML for alias list: {e}")

    alias_data_json = "{}"
    alias_list_json = "[]"
    
    # Defaults
    alias_dict = {a: [0]*len(dates) for a in all_configured_aliases}
    
    # Store today's buy/sell for the bar chart
    today_alias_stats = {a: {'buy': 0, 'sell': 0} for a in all_configured_aliases}
    latest_date_str = str(dates[-1])

    if os.path.exists(alias_history_file):
        try:
            df_alias = pd.read_csv(alias_history_file)
            if not df_alias.empty:
                # Pivot: Index=date, Cols=alias, Values=net_buy
                # Ensure date column is string for matching
                df_alias['date'] = df_alias['date'].astype(str)
                df_pivot = df_alias.pivot_table(index='date', columns='alias', values='net_buy', aggfunc='sum')
                
                # Reindex to match the main report dates (dates list defined above)
                # Fill missing with 0
                df_pivot = df_pivot.reindex(dates, fill_value=0).fillna(0)
                
                # Update alias_dict with real data
                for col in df_pivot.columns:
                    col_str = str(col)
                    alias_dict[col_str] = df_pivot[col].tolist()
                
                # Extract today's buy/sell if available columns exist
                if 'buy' in df_alias.columns and 'sell' in df_alias.columns:
                    df_today = df_alias[df_alias['date'] == latest_date_str]
                    for _, row in df_today.iterrows():
                        a_name = str(row['alias'])
                        if a_name in today_alias_stats:
                             today_alias_stats[a_name]['buy'] = row['buy']
                             today_alias_stats[a_name]['sell'] = row['sell']
                        else:
                             # In case of new aliases not in config
                             today_alias_stats[a_name] = {'buy': row['buy'], 'sell': row['sell']}
                    
        except Exception as e:
            print(f"Error processing alias history: {e}")
            
    # Serialize
    alias_data_json = json.dumps(alias_dict, ensure_ascii=False)
    # Sort aliases list (using all keys in dict, which includes both configured and seen-history)
    alias_list_json = json.dumps(sorted(list(alias_dict.keys())), ensure_ascii=False)
    
    # Prepare Today's Data for Bar Chart
    # Sort by Total Volume (Buy + Sell) desc
    sorted_aliases_today = sorted(today_alias_stats.keys(), key=lambda x: today_alias_stats[x]['buy'] + today_alias_stats[x]['sell'], reverse=True)
    today_bar_data = {
        'names': sorted_aliases_today,
        'buys': [today_alias_stats[a]['buy'] for a in sorted_aliases_today],
        'sells': [today_alias_stats[a]['sell'] for a in sorted_aliases_today]
    }
    today_bar_json = json.dumps(today_bar_data, ensure_ascii=False)

    # 4. Load Stock Map for Individual Stock Details Table
    stock_details_html = ""
    stock_map_file = os.path.join(OUTPUT_DIR, 'lhb_latest_stock_map.json')
    if os.path.exists(stock_map_file):
        try:
            with open(stock_map_file, 'r', encoding='utf-8') as f:
                stock_data = json.load(f)
                
            # Build Table Rows
            rows_html = ""
            for s in stock_data:
                # Stock Header Row
                # Check key existence safely
                s_code = s.get('code', s.get('stock_code', 'Unknown'))
                s_name = s.get('name', s.get('stock_name', 'Unknown'))
                s_net = s.get('net_buy', 0)
                
                net_color = '#e74c3c' if s_net > 0 else '#2ecc71'
                net_str = f"{s_net/10000:.0f}万"
                
                rows_html += f"""
                <tr style="background-color: #f0f4f8; font-weight: bold;">
                    <td colspan="4" style="text-align: left; padding-left: 15px;">
                        {s_code} {s_name} 
                        <span style="float: right; color: {net_color}; margin-right: 10px;">净买: {net_str}</span>
                    </td>
                </tr>
                """
                
                # Branch Rows (Top 10 max)
                branches = s.get('branches', [])
                for i, b in enumerate(branches[:10]):
                    alias_span = f"<span style='color: #8e44ad; font-weight: bold; margin-left:8px;'>[{b['alias']}]</span>" if b.get('alias') else ""
                    cat_span = f"<span style='color: #2980b9; font-size: 0.9em; margin-left:5px;'>({b['category']})</span>" if b.get('category') else ""
                    b_net = b.get('net', 0)
                    b_net_color = '#e74c3c' if b_net > 0 else '#2ecc71'
                    
                    rows_html += f"""
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="text-align: left; padding-left: 30px; color: #555; font-size: 0.95em;">
                            {i+1}. {b.get('branch')} {alias_span} {cat_span}
                        </td>
                        <td style="color: #e74c3c;">{b.get('buy', 0)/10000:.0f}</td>
                        <td style="color: #2ecc71;">{b.get('sell', 0)/10000:.0f}</td>
                        <td style="color: {b_net_color}; font-weight: bold;">{b_net/10000:.0f}</td>
                    </tr>
                    """

            
            stock_details_html = f"""
            <div class="card">
                <h2>个股龙虎榜详情 (Top Stocks)</h2>
                <div style="height: 500px; overflow-y: auto; border: 1px solid #eee;">
                    <table class="summary-table" style="font-size: 13px;">
                        <thead style="position: sticky; top: 0; background: white; z-index: 1;">
                            <tr>
                                <th style="width: 50%;">营业部名称 (别名/分类)</th>
                                <th style="width: 15%;">买入(万)</th>
                                <th style="width: 15%;">卖出(万)</th>
                                <th style="width: 15%;">净买(万)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
            """
            
        except Exception as e:
            print(f"Error loading stock map: {e}")

    def create_html(echarts_path):
        # Ensure stock_details_html is interpolated
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>龙虎榜资金画像日报 - {dates[-1]}</title>
    <script src="{echarts_path}"></script>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background-color: #f5f7fa; }}
        .header {{ text-align: center; margin-bottom: 20px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        h1 {{ margin: 0; color: #333; }}
        h2 {{ color: #444; border-left: 5px solid #3498db; padding-left: 10px; margin-top: 0; }}
        .chart-container {{ width: 100%; height: 400px; }}
        .summary-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .summary-table th, .summary-table td {{ border: 1px solid #eee; padding: 8px; text-align: center; }}
        .summary-table th {{ background-color: #f8f9fa; }}
        .positive {{ color: #e74c3c; font-weight: bold; }}
        .negative {{ color: #2ecc71; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>龙虎榜资金画像日报</h1>
        <p>日期: {dates[-1]}</p>
    </div>

    <!-- 0.0 个股详情 (新增) -->
    {stock_details_html}

    <!-- 0.1 当日游资买卖总量透视 (新增) -->
    <div class="card">
        <h2>当日知名席位买卖总额排行</h2>
        <div id="daily_bar_chart" class="chart-container" style="height: 500px;"></div>
    </div>

    <!-- 0. 知名席位透视 -->
    <div class="card">
        <h2>知名席位(游资/机构) 资金透视</h2>
        <div style="margin-bottom: 15px; display: flex; align-items: center;">
            <label for="alias_select" style="font-weight: bold; margin-right: 10px;">选择席位:</label>
            <select id="alias_select" onchange="updateAliasChart()" style="padding: 6px; font-size: 15px; border-radius: 4px; border: 1px solid #ccc; min-width: 200px;">
                <!-- JS populated -->
            </select>
            <span style="font-size: 12px; color: #888; margin-left: 10px;">(数据来源: 包含该席位的上榜个股净买入之和)</span>
        </div>
        <div id="alias_chart" class="chart-container" style="height: 350px;"></div>
    </div>

    <!-- 1. 核心资金净买入趋势 -->
    <div class="card">
        <h2>主力资金净买入趋势 (近5日)</h2>
        <div id="main_fund_chart" class="chart-container"></div>
    </div>

    <!-- 2. 分项资金详情 -->
    <div class="card">
        <h2>各路资金独立走势</h2>
        <div id="sub_fund_chart" class="chart-container"></div>
    </div>

    <!-- 3. 龙虎榜成交额与占比 -->
    <div class="card">
        <h2>龙虎榜成交活跃度</h2>
        <div id="turnover_chart" class="chart-container"></div>
    </div>

    <script>
        // Common Config
        var dates = {dates};

        // --- Daily Bar Chart ---
        var dailyBarData = {today_bar_json};
        
        var chartDailyBar = echarts.init(document.getElementById('daily_bar_chart'));
        var optionDailyBar = {{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
            legend: {{ data: ['买入金额', '卖出金额'] }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'value', axisLabel: {{ formatter: function(v){{ return (v/10000).toFixed(0) + '万'; }} }} }},
            yAxis: {{ type: 'category', data: dailyBarData.names, inverse: true }},
            series: [
                {{
                    name: '买入金额',
                    type: 'bar',
                    stack: 'total',
                    label: {{ show: true, position: 'right', formatter: function(p){{ return p.value > 0 ? (p.value/10000).toFixed(0) : ''; }} }},
                    itemStyle: {{ color: '#e74c3c' }},
                    data: dailyBarData.buys
                }},
                {{
                    name: '卖出金额',
                    type: 'bar',
                    stack: 'total',
                    label: {{ show: true, position: 'left', formatter: function(p){{ return p.value > 0 ? (p.value/10000).toFixed(0) : ''; }} }},
                    itemStyle: {{ color: '#2ecc71' }},
                    data: dailyBarData.sells.map(function(val) {{ return -val; }}) // Negative for visuals? No, standard stacked bar usually positive. Check user requirement? "Buy Sell Total". Usually side-by-side or stacked.
                    // If stacked, Sell usually shown as outflow? 
                    // Let's use Positive 'Sell' values but stack them? 
                    // Or "Butterfly Chart"? Left Buy, Right Sell?
                    // Let's do standard grouped bar or stacked.
                    // User asked for "Buy Sell Total Diagram".
                    // Let's try grouped bar for clarity.
                }}
            ]
        }};
        
        // Butterfly Chart Adjustment
        optionDailyBar = {{
            tooltip: {{ 
                trigger: 'axis', 
                axisPointer: {{ type: 'shadow' }},
                formatter: function (params) {{
                    var tar0 = params[0];
                    var tar1 = params[1];
                    return tar0.name + '<br/>' + tar0.seriesName + ' : ' + (tar0.value/10000).toFixed(0) + '万<br/>' + tar1.seriesName + ' : ' + (Math.abs(tar1.value)/10000).toFixed(0) + '万';
                }}
            }},
            legend: {{ data: ['买入金额', '卖出金额'] }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ 
                type: 'value', 
                axisLabel: {{ formatter: function(v){{ return (Math.abs(v)/10000).toFixed(0) + '万'; }} }}
            }},
            yAxis: {{ type: 'category', data: dailyBarData.names, inverse: true }},
            series: [
                {{
                    name: '买入金额',
                    type: 'bar',
                    stack: 'total',
                    label: {{ show: true, position: 'right', formatter: function(p){{ return (p.value/10000).toFixed(0); }} }},
                    itemStyle: {{ color: '#e74c3c' }},
                    data: dailyBarData.buys
                }},
                {{
                    name: '卖出金额',
                    type: 'bar',
                    stack: 'total',
                    label: {{ show: true, position: 'left', formatter: function(p){{ return (Math.abs(p.value)/10000).toFixed(0); }} }},
                    itemStyle: {{ color: '#2ecc71' }},
                    data: dailyBarData.sells.map(function(v){{ return -v; }})
                }}
            ]
        }};
        
        chartDailyBar.setOption(optionDailyBar);

        // --- Alias Data & Chart ---
        var aliasData = {alias_data_json};
        var aliasList = {alias_list_json};
        
        var chartAlias = echarts.init(document.getElementById('alias_chart'));
        
        function updateAliasChart() {{
            var select = document.getElementById('alias_select');
            var selected = select.value;
            if (!selected && aliasList.length > 0) selected = aliasList[0];
            if (!selected) return;
            
            var dataSeries = aliasData[selected];
            
            var optionAlias = {{
                title: {{ text: selected + ' 近期净买入趋势', left: 'center', textStyle: {{ fontSize: 16 }} }},
                tooltip: {{ trigger: 'axis' }},
                grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
                xAxis: {{ type: 'category', boundaryGap: false, data: dates }},
                yAxis: {{ type: 'value', name: '净买入(元)', axisLabel: {{ formatter: function(v){{ return (v/10000).toFixed(0) + '万'; }} }} }},
                series: [{{
                    name: selected,
                    type: 'line',
                    data: dataSeries,
                    smooth: true,
                    showSymbol: false,
                    itemStyle: {{ color: '#8e44ad' }},
                    areaStyle: {{ opacity: 0.2 }}
                }}]
            }};
            chartAlias.setOption(optionAlias);
        }}

        // Init Dropdown and First Chart
        var selectEl = document.getElementById('alias_select');
        if (aliasList && aliasList.length > 0) {{
            aliasList.forEach(function(a) {{
                var opt = document.createElement('option');
                opt.value = a;
                opt.innerText = a;
                selectEl.appendChild(opt);
            }});
            // Trigger
            updateAliasChart();
        }} else {{
            document.getElementById('alias_chart').innerHTML = '<p style="text-align:center;padding-top:100px;color:#999">暂无席位明细数据</p>';
        }}
        
        window.addEventListener('resize', function(){{ 
            chartDailyBar.resize();
            chartAlias.resize(); 
            chart1.resize();
            chart2.resize();
            chart3.resize();
        }});

        // 1. Main Fund Chart (Combined Net Buy)
        var chart1 = echarts.init(document.getElementById('main_fund_chart'));
        var option1 = {{
            tooltip: {{ trigger: 'axis' }},
            legend: {{ data: ['网红游资', '高频量化', '机构', '外资'] }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'category', boundaryGap: false, data: dates }},
            yAxis: {{ type: 'value', name: '净买入(元)', axisLabel: {{ formatter: function(v){{ return v/10000 + '万'; }} }} }},
            series: [
                {{ name: '网红游资', type: 'line', data: {hot_money}, smooth: true, itemStyle: {{ color: '#e74c3c' }} }},
                {{ name: '高频量化', type: 'line', data: {quant}, smooth: true, itemStyle: {{ color: '#3498db' }} }},
                {{ name: '机构', type: 'line', data: {inst}, smooth: true, itemStyle: {{ color: '#f1c40f' }} }},
                {{ name: '外资', type: 'line', data: {foreign}, smooth: true, itemStyle: {{ color: '#9b59b6' }} }}
            ]
        }};
        chart1.setOption(option1);

        // 2. Turnover Chart
        var chart2 = echarts.init(document.getElementById('turnover_chart'));
        var option2 = {{
            tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
            legend: {{ data: ['龙虎榜成交额', '占全市场比例(%)'] }},
            grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
            xAxis: {{ type: 'category', data: dates }},
            yAxis: [
                {{ type: 'value', name: '成交额(元)', position: 'left', axisLabel: {{ formatter: function(v){{ return v/100000000 + '亿'; }} }} }},
                {{ type: 'value', name: '比例(%)', position: 'right', axisLabel: {{ formatter: '{{value}} %' }} }}
            ],
            series: [
                {{ name: '龙虎榜成交额', type: 'bar', data: {lhb_turnover}, itemStyle: {{ color: '#95a5a6' }} }},
                {{ name: '占全市场比例(%)', type: 'line', yAxisIndex: 1, data: {lhb_ratio}, smooth: true, itemStyle: {{ color: '#e67e22' }}, markPoint: {{ data: [{{ type: 'max', name: '最大值' }}] }} }}
            ]
        }};
        chart2.setOption(option2);

        // 3. Sub Charts (Breakdown) if needed. 
        // For brevity, combined chart 1 covers most needs, but let's do a stacked area or just separate lines
        // Let's make "sub_fund_chart" a stacked bar to see composition of net buy? 
        // Or maybe Cumulative Net Buy?
        // Requirement says "Net Buy Change" which usually means daily net buy over time. Consolidating into Chart 1 is good.
        // Let's use Chart 3 area for simple separate lines to avoid clutter if needed, or maybe "Cumulative".
        // Let's display the "Hot Money" specifically as requried.
        
        var chart3 = echarts.init(document.getElementById('sub_fund_chart'));
        var option3 = {{
            title: {{ text: '网红游资与机构博弈' }},
            tooltip: {{ trigger: 'axis' }},
            legend: {{ data: ['网红游资', '机构'] }},
            xAxis: {{ type: 'category', boundaryGap: false, data: dates }},
            yAxis: {{ type: 'value' }},
            series: [
                {{ 
                    name: '网红游资', 
                    type: 'line', 
                    areaStyle: {{ opacity: 0.1 }},
                    data: {hot_money},
                    itemStyle: {{ color: '#e74c3c' }},
                    markLine: {{ data: [{{ type: 'average', name: 'Avg' }}] }}
                }},
                {{ 
                    name: '机构', 
                    type: 'line', 
                    areaStyle: {{ opacity: 0.1 }},
                    data: {inst},
                    itemStyle: {{ color: '#f1c40f' }}
                }}
            ]
        }};
        chart3.setOption(option3);


    </script>
</body>
</html>
    """
    
    # Write to local output (Deep path needs ../../../)
    # Path: service/LHB_Analyse/output/lhb_analysis_report.html
    # Use CDN for better compatibility
    cdn_url = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(create_html(cdn_url))
    
    # Write to shared reports (Same folder path needs ./)
    # Path: share_reports/lhb_analysis_report.html
    try:
        with open(SHARED_REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(create_html(cdn_url))
    except:
        pass
        
    print(f"Report generated at {REPORT_FILE}")

if __name__ == "__main__":
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        generate_html(df)
    else:
        print("No history file found.")
