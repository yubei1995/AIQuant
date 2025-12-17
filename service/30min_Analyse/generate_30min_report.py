import json
import os
import sys

def generate_30min_report(json_path, output_path):
    if not os.path.exists(json_path):
        print(f"Error: Data file not found {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data_map = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    block_names = list(data_map.keys())
    if not block_names:
        print("No data to visualize.")
        return
        
    # 1. Prepare Data for Ranking
    # Calculate latest return for each block
    block_stats = []
    for name in block_names:
        values = data_map[name]['values']
        last_val = values[-1] if values else 0
        block_stats.append({'name': name, 'value': last_val})
        
    # Sort descending
    block_stats.sort(key=lambda x: x['value'], reverse=True)
    
    sorted_names = [x['name'] for x in block_stats]
    sorted_values = [x['value'] for x in block_stats]
    
    # Common Time Axis
    times = data_map[block_names[0]]['times']

    html_content = f"""
<!DOCTYPE html>
<html style="height: 100%">
   <head>
       <meta charset="utf-8">
       <title>30-Min Block Analysis</title>
       <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
       <style>
           body {{ margin: 0; height: 100%; font-family: sans-serif; overflow: hidden; }}
           .header {{
               height: 40px;
               background: #f4f4f4;
               display: flex;
               align-items: center;
               padding: 0 20px;
               border-bottom: 1px solid #ddd;
           }}
           .header h2 {{ margin: 0; font-size: 18px; margin-right: 20px; }}
           button {{
               padding: 5px 15px;
               cursor: pointer;
               font-size: 14px;
               background: #fff;
               border: 1px solid #ccc;
               border-radius: 4px;
               margin-right: 10px;
           }}
           button:hover {{ background: #e6e6e6; }}
           
           #rank_container {{ height: 35%; border-bottom: 1px solid #eee; }}
           
           /* Wrapper for Trend Chart to position button */
           #trend_wrapper {{
               height: calc(65% - 40px);
               position: relative;
               width: 100%;
           }}
           #trend_container {{ width: 100%; height: 100%; }}
           
           #back_btn {{
               display: none; /* Hidden by default */
               position: absolute;
               top: 10px;
               left: 60px; /* Adjust based on Y-axis width */
               z-index: 100;
               background-color: #e3f2fd;
               border-color: #2196f3;
               color: #0d47a1;
               font-weight: bold;
               box-shadow: 0 2px 4px rgba(0,0,0,0.1);
           }}
       </style>
   </head>
   <body>
       <div class="header">
           <h2>30-Min Block Analysis</h2>
           <button onclick="resetView()">Reset Zoom (Top 5)</button>
           <span style="margin-left: 20px; color: #666; font-size: 12px;">* Click bars/lines to isolate. Slider highlights range.</span>
       </div>
       
       <div id="rank_container"></div>
       
       <div id="trend_wrapper">
           <button id="back_btn" onclick="exitIsolation()">← Back to Overview</button>
           <div id="trend_container"></div>
       </div>
       
       <script type="text/javascript">
            var rawData = {json.dumps(data_map, ensure_ascii=False)};
            var sortedNames = {json.dumps(sorted_names, ensure_ascii=False)};
            var sortedValues = {json.dumps(sorted_values, ensure_ascii=False)};
            var allTimes = {json.dumps(times, ensure_ascii=False)};
            
            // State
            var isIsolated = false;
            var defaultTopN = 5;
            
            // Generate distinct colors for all blocks
            var colors = [
                '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc',
                '#c23531', '#2f4554', '#61a0a8', '#d48265', '#91c7ae', '#749f83', '#ca8622', '#bda29a', '#6e7074',
                '#546570', '#c4ccd3', '#f05b72', '#ef5b9c', '#f47920', '#905a3d', '#fab27b', '#2a5caa', '#444693',
                '#726930', '#b2d235', '#6d8346', '#ac6767', '#1d953f', '#6950a1', '#918597'
            ];
            
            var colorMap = {{}};
            sortedNames.forEach((name, idx) => {{
                colorMap[name] = colors[idx % colors.length];
            }});

            // --- 1. Rank Chart (Bar) ---
            var rankChart = echarts.init(document.getElementById("rank_container"));
            
            var rankOption = {{
                title: {{ text: 'Performance Ranking (All)', left: 10, top: 5, textStyle: {{ fontSize: 14 }} }},
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '3%', right: '3%', bottom: '15%', top: '30px', containLabel: true }},
                // Use two x-axes: one for display (static), one for slider control (hidden)
                xAxis: [
                    {{ 
                        type: 'category', 
                        data: sortedNames,
                        axisLabel: {{ 
                            interval: 0, 
                            rotate: 45, 
                            fontSize: 9,
                            color: '#333' // Default label color
                        }}
                    }},
                    {{
                        type: 'category',
                        data: sortedNames,
                        show: false // Hidden axis for slider
                    }}
                ],
                yAxis: {{ type: 'value', splitLine: {{ show: false }} }},
                dataZoom: [
                    {{ 
                        type: 'slider', 
                        xAxisIndex: 1, // Control the hidden axis
                        show: true, 
                        startValue: 0, 
                        endValue: 4, // Default Top 5
                        height: 20,
                        bottom: 5,
                        brushSelect: false,
                        handleSize: '100%'
                    }}
                ],
                series: [{{
                    name: 'Return %',
                    type: 'bar',
                    xAxisIndex: 0, // Bind series to the visible static axis
                    data: sortedValues, // Initial data
                    itemStyle: {{
                        color: '#ccc' // Default placeholder
                    }}
                }}]
            }};
            rankChart.setOption(rankOption);
            
            // --- 2. Trend Chart (Line) ---
            var trendChart = echarts.init(document.getElementById("trend_container"));
            
            var seriesList = [];
            
            // Create Line Series for ALL blocks (Top Chart: Fixed Weight)
            sortedNames.forEach(function(name) {{
                var data = rawData[name];
                seriesList.push({{
                    name: name,
                    type: 'line',
                    xAxisIndex: 0,
                    yAxisIndex: 0,
                    data: data.values.map((val, idx) => [allTimes[idx], val]),
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {{ width: 2, color: colorMap[name] }},
                    itemStyle: {{ color: colorMap[name] }},
                    emphasis: {{ focus: 'series', lineStyle: {{ width: 4 }} }}
                }});
            }});
            
            // Create Line Series for ALL blocks (Bottom Chart: Dynamic Weight)
            // We use the same name so legend toggles both? 
            // ECharts allows duplicate names.
            sortedNames.forEach(function(name) {{
                var data = rawData[name];
                // Check if dynamic_values exists (it should with new backend)
                var dynVals = data.dynamic_values || data.values; 
                
                seriesList.push({{
                    name: name, // Same name to link with top chart
                    type: 'line',
                    xAxisIndex: 1,
                    yAxisIndex: 2, // Left axis of bottom grid
                    data: dynVals.map((val, idx) => [allTimes[idx], val]),
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {{ width: 2, color: colorMap[name], type: 'dashed' }}, // Dashed to distinguish? Or solid?
                    itemStyle: {{ color: colorMap[name] }},
                    emphasis: {{ focus: 'series', lineStyle: {{ width: 4 }} }}
                }});
            }});
            
            // Add Cumulative Volume Series (Hidden by default) - Put on Top Chart (Right Axis)
            seriesList.push({{
                name: 'CumVolume',
                type: 'bar',
                xAxisIndex: 0,
                yAxisIndex: 1, // Right axis of top grid
                data: [],
                itemStyle: {{ color: 'rgba(100, 100, 100, 0.2)' }},
                barMaxWidth: 20
            }});

            // Add Interval Volume Series (Hidden by default) - Put on Bottom Chart (Right Axis)
            seriesList.push({{
                name: 'Volume',
                type: 'bar',
                xAxisIndex: 1,
                yAxisIndex: 3, // Right axis of bottom grid
                data: [],
                itemStyle: {{ color: 'rgba(100, 100, 100, 0.3)' }},
                barMaxWidth: 20
            }});
            
            var trendOption = {{
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{ type: 'cross' }},
                    order: 'valueDesc',
                    formatter: function (params) {{
                        // Custom tooltip to show both charts info clearly
                        return params[0].name + '<br/>' + params.map(p => {{
                            var val = Array.isArray(p.value) ? p.value[1] : p.value;
                            if (p.seriesName === 'Volume') return p.marker + 'Interval Vol: ' + (val/100000000).toFixed(2) + '亿';
                            if (p.seriesName === 'CumVolume') return p.marker + 'Cum Vol: ' + (val/100000000).toFixed(2) + '亿';
                            
                            var label = p.seriesName;
                            if (p.axisIndex === 1) label += ' (Dynamic)';
                            return p.marker + label + ': ' + val + '%';
                        }}).join('<br/>');
                    }}
                }},
                legend: {{ show: false }},
                axisPointer: {{ link: [{{ xAxisIndex: 'all' }}] }}, // Sync crosshair
                grid: [
                    {{ left: '3%', right: '3%', top: '30px', height: '45%', containLabel: true }}, // Top Grid
                    {{ left: '3%', right: '3%', top: '55%', height: '40%', containLabel: true }}   // Bottom Grid
                ],
                xAxis: [
                    {{ type: 'category', boundaryGap: false, data: allTimes, gridIndex: 0, axisLabel: {{ show: false }} }}, // Top X (Hidden labels)
                    {{ type: 'category', boundaryGap: false, data: allTimes, gridIndex: 1 }}  // Bottom X
                ],
                yAxis: [
                    {{ type: 'value', name: 'Cum. Weight (%)', position: 'left', scale: true, gridIndex: 0 }}, // Top Left
                    {{ 
                        type: 'value', 
                        name: 'Cum. Volume', 
                        position: 'right', 
                        splitLine: {{ show: false }},
                        axisLabel: {{ formatter: v => (v/100000000).toFixed(1) + '亿' }},
                        gridIndex: 0 
                    }}, // Top Right
                    {{ type: 'value', name: 'Interval Weight (%)', position: 'left', scale: true, gridIndex: 1 }}, // Bottom Left
                    {{ 
                        type: 'value', 
                        name: 'Interval Volume', 
                        position: 'right', 
                        splitLine: {{ show: false }},
                        axisLabel: {{ formatter: v => (v/100000000).toFixed(1) + '亿' }},
                        gridIndex: 1
                    }} // Bottom Right
                ],
                series: seriesList
            }};
            trendChart.setOption(trendOption);
            
            // --- Logic ---
            
            function updateTrendVisibility() {{
                if (isIsolated) return;
                
                // Get range from the slider (which controls axis 1)
                var model = rankChart.getModel().getComponent('dataZoom', 0);
                var start = model.option.startValue;
                var end = model.option.endValue;
                
                // Handle percent case if values are not set
                if (start == null) {{
                     var range = model.getPercentRange();
                     start = Math.floor(range[0] * sortedNames.length / 100);
                     end = Math.floor(range[1] * sortedNames.length / 100);
                }}
                
                // Ensure bounds
                if (start < 0) start = 0;
                if (end >= sortedNames.length) end = sortedNames.length - 1;
                
                // 1. Update Trend Chart Visibility
                var visibleNames = sortedNames.slice(start, end + 1);
                var newSelected = {{}};
                sortedNames.forEach(n => newSelected[n] = false);
                visibleNames.forEach(n => newSelected[n] = true);
                
                trendChart.setOption({{
                    legend: {{ selected: newSelected }},
                    series: [
                        {{ name: 'CumVolume', data: [] }}, // Clear cum volume
                        {{ name: 'Volume', data: [] }} // Clear volume
                    ]
                }});
                
                // 2. Update Rank Chart Colors (Gray out non-selected)
                var newBarData = sortedNames.map((name, idx) => {{
                    var val = sortedValues[idx];
                    var col = (idx >= start && idx <= end) ? colorMap[name] : '#e0e0e0';
                    return {{
                        value: val,
                        itemStyle: {{ color: col }}
                    }};
                }});
                
                rankChart.setOption({{
                    series: [{{
                        data: newBarData
                    }}]
                }});
            }}
            
            // Listen to DataZoom
            rankChart.on('datazoom', function (params) {{
                setTimeout(updateTrendVisibility, 0);
            }});
            
            // Initial Sync
            updateTrendVisibility();
            
            // --- Isolation Logic ---
            
            function isolateBlock(name) {{
                isIsolated = true;
                document.getElementById('back_btn').style.display = 'block';
                
                var newSelected = {{}};
                sortedNames.forEach(n => newSelected[n] = false);
                newSelected[name] = true;
                
                var volData = rawData[name].volumes;
                var cumVolData = rawData[name].cum_volumes;
                
                trendChart.setOption({{
                    legend: {{ selected: newSelected }},
                    series: [
                        {{ name: 'CumVolume', data: cumVolData }},
                        {{ name: 'Volume', data: volData }}
                    ]
                }});
                
                // Optional: Highlight only the isolated bar in Rank Chart
                var newBarData = sortedNames.map((n, idx) => {{
                    var val = sortedValues[idx];
                    var col = (n === name) ? colorMap[n] : '#e0e0e0';
                    return {{
                        value: val,
                        itemStyle: {{ color: col }}
                    }};
                }});
                rankChart.setOption({{ series: [{{ data: newBarData }}] }});
            }}
            
            window.exitIsolation = function() {{
                isIsolated = false;
                document.getElementById('back_btn').style.display = 'none';
                updateTrendVisibility(); // Restore view based on current slider
            }};
            
            // Click Events
            rankChart.on('click', function(params) {{
                isolateBlock(params.name);
            }});
            
            trendChart.on('click', function(params) {{
                if (params.componentType === 'series' && params.seriesType === 'line') {{
                    isolateBlock(params.seriesName);
                }}
            }});

            window.resetView = function() {{
                if (isIsolated) exitIsolation();
                rankChart.dispatchAction({{
                    type: 'dataZoom',
                    startValue: 0,
                    endValue: 4
                }});
            }};
            
            window.addEventListener('resize', function() {{
                rankChart.resize();
                trendChart.resize();
            }});
       </script>
   </body>
</html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML report generated: {output_path}")

if __name__ == "__main__":
    # Test usage
    from datetime import datetime
    current_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime("%Y%m%d")
    json_file = os.path.join(current_dir, "output", f"30min_data_{date_str}.json")
    html_file = os.path.join(current_dir, "output", f"30min_analysis_{date_str}.html")
    
    generate_30min_report(json_file, html_file)
