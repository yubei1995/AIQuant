import pandas as pd
import os
import sys

def generate_html_report(csv_path, output_path):
    if not os.path.exists(csv_path):
        print(f"Error: File not found {csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Sort by 1d(%) descending to get Top 20 performers
    # Or should we sort by Turnover? Usually "Top 20" in this context implies performance or hotness.
    # Let's sort by 1d(%) as per previous logic.
    if '1d(%)' in df.columns:
        df = df.sort_values('1d(%)', ascending=False)
    
    # Show all blocks as requested
    plot_data = df
    
    # Prepare data for ECharts
    blocks = plot_data['细分板块'].tolist()
    data_1d = plot_data['1d(%)'].tolist()
    data_3d = plot_data['3d(%)'].tolist()
    data_5d = plot_data['5d(%)'].tolist()
    data_10d = plot_data['10d(%)'].tolist()
    
    # HTML Template with ECharts
    html_content = f"""
<!DOCTYPE html>
<html style="height: 100%">
   <head>
       <meta charset="utf-8">
       <title>Global Block Analysis (All)</title>
       <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
   </head>
   <body style="height: 100%; margin: 0">
       <div id="container" style="height: 100%"></div>
       <script type="text/javascript">
            var dom = document.getElementById("container");
            var myChart = echarts.init(dom);
            var app = {{}};
            
            var option;

            option = {{
                title: {{
                    text: 'Global Block Analysis - Multi-Period Returns',
                    subtext: 'Double-click legend to isolate series',
                    left: 'center'
                }},
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{
                        type: 'shadow'
                    }}
                }},
                legend: {{
                    data: ['1d(%)', '3d(%)', '5d(%)', '10d(%)'],
                    top: 'bottom'
                    // selectedMode: 'single' removed to show all initially
                }},
                grid: {{
                    left: '2%',
                    right: '2%',
                    bottom: '10%',
                    containLabel: true
                }},
                dataZoom: [
                    {{
                        type: 'slider',
                        show: true,
                        xAxisIndex: [0],
                        start: 0,
                        end: 100
                    }},
                    {{
                        type: 'inside',
                        xAxisIndex: [0],
                        start: 0,
                        end: 100
                    }}
                ],
                xAxis: [
                    {{
                        type: 'category',
                        data: {blocks},
                        axisLabel: {{
                            interval: 0,
                            rotate: 45,
                            fontSize: 10
                        }}
                    }}
                ],
                yAxis: [
                    {{
                        type: 'value',
                        name: 'Return (%)',
                        axisLabel: {{
                            formatter: '{{value}} %'
                        }}
                    }}
                ],
                series: [
                    {{
                        name: '1d(%)',
                        type: 'bar',
                        emphasis: {{ focus: 'series' }},
                        data: {data_1d},
                        itemStyle: {{ color: '#5470c6' }},
                        barMaxWidth: 20
                    }},
                    {{
                        name: '3d(%)',
                        type: 'bar',
                        emphasis: {{ focus: 'series' }},
                        data: {data_3d},
                        itemStyle: {{ color: '#91cc75' }},
                        barMaxWidth: 20
                    }},
                    {{
                        name: '5d(%)',
                        type: 'bar',
                        emphasis: {{ focus: 'series' }},
                        data: {data_5d},
                        itemStyle: {{ color: '#fac858' }},
                        barMaxWidth: 20
                    }},
                    {{
                        name: '10d(%)',
                        type: 'bar',
                        emphasis: {{ focus: 'series' }},
                        data: {data_10d},
                        itemStyle: {{ color: '#ee6666' }},
                        barMaxWidth: 20
                    }}
                ]
            }};

            if (option && typeof option === 'object') {{
                myChart.setOption(option);
            }}

            window.addEventListener('resize', myChart.resize);
       </script>
   </body>
</html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML report generated: {output_path}")

if __name__ == "__main__":
    from datetime import datetime
    # Default paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    date_str = datetime.now().strftime("%Y%m%d")
    csv_file = os.path.join(current_dir, "output", f"global_analysis_details_{date_str}.csv")
    html_file = os.path.join(current_dir, "output", f"global_analysis_report_{date_str}.html")
    
    generate_html_report(csv_file, html_file)
