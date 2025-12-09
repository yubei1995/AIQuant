"""
光模块板块加权分析 (基于成交额权重)
"""
import sys
import os
from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Alignment, PatternFill

# 添加项目根目录到路径
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.data_fetch.stock_data import StockDataFetcher
from examples.Optical_Module import config

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def calculate_weighted_change(df: pd.DataFrame) -> float:
    """
    计算加权涨跌幅 (使用成交额作为权重)
    """
    if df.empty or df['成交额'].sum() == 0:
        return 0.0
    
    # 权重 = 成交额 / 总成交额
    weights = df['成交额'] / df['成交额'].sum()
    weighted_change = (df['涨跌幅'] * weights).sum()
    return weighted_change

def generate_chart(df: pd.DataFrame, output_dir: str) -> str:
    """
    生成个股涨跌幅柱状图
    """
    # 按涨跌幅排序
    df_sorted = df.sort_values('涨跌幅', ascending=True)
    
    plt.figure(figsize=(12, 8))
    
    # 颜色映射：涨红跌绿
    colors = ['red' if x >= 0 else 'green' for x in df_sorted['涨跌幅']]
    
    bars = plt.barh(df_sorted['名称'], df_sorted['涨跌幅'], color=colors)
    
    plt.title('光模块板块个股涨跌幅 (实时)', fontsize=16)
    plt.xlabel('涨跌幅 (%)', fontsize=12)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # 添加数值标签
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + 0.1 if width >= 0 else width - 0.5
        plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.2f}%', 
                 va='center', fontsize=10)
                 
    plt.tight_layout()
    
    chart_path = os.path.join(output_dir, "optical_module_chart.png")
    plt.savefig(chart_path)
    plt.close()
    return chart_path

def generate_excel_report(df_summary: pd.DataFrame, df_details: pd.DataFrame, chart_path: str, output_dir: str):
    """
    生成Excel报告
    """
    excel_path = os.path.join(output_dir, "optical_module_report.xlsx")
    
    # 排序详情：按成交额降序
    df_details_sorted = df_details.sort_values('成交额', ascending=False)
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='板块概览', index=False)
        df_details_sorted.to_excel(writer, sheet_name='个股详情', index=False)
        
    # 格式化Excel
    wb = openpyxl.load_workbook(excel_path)
    
    # 1. 格式化板块概览
    ws_summary = wb['板块概览']
    # 调整列宽
    for col in ws_summary.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        ws_summary.column_dimensions[column].width = adjusted_width
        
    # 2. 格式化个股详情
    ws_details = wb['个股详情']
    # 调整列宽
    for col in ws_details.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        ws_details.column_dimensions[column].width = adjusted_width
        
    # 插入图表
    if os.path.exists(chart_path):
        img = Image(chart_path)
        # 插入到详情页的右侧
        ws_details.add_image(img, 'H2')
        
    wb.save(excel_path)
    print(f"✅ Excel报告已生成: {excel_path}")

def main():
    print("=" * 50)
    print("开始光模块(CPO)板块加权分析 (基于成交额)")
    print("=" * 50)
    
    # 1. 获取数据
    fetcher = StockDataFetcher()
    stock_codes = list(config.ALL_STOCKS.keys())
    
    print(f"正在获取 {len(stock_codes)} 只股票的实时行情...")
    df = fetcher.get_stock_realtime_batch(stock_codes)
    
    if df is None or df.empty:
        print("❌ 未获取到数据，程序结束")
        return
        
    # 2. 计算板块加权涨跌幅
    weighted_change = calculate_weighted_change(df)
    total_turnover = df['成交额'].sum()
    avg_change = df['涨跌幅'].mean()
    
    print(f"\n板块加权涨跌幅: {weighted_change:.2f}%")
    print(f"板块平均涨跌幅: {avg_change:.2f}%")
    print(f"板块总成交额: {total_turnover/100000000:.2f} 亿")
    
    # 3. 准备数据
    # 汇总数据
    summary_data = {
        '板块名称': ['光模块(CPO)'],
        '加权涨跌幅': [weighted_change],
        '平均涨跌幅': [avg_change],
        '总成交额(亿)': [total_turnover / 100000000],
        '股票数量': [len(df)],
        '更新时间': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    df_summary = pd.DataFrame(summary_data)
    
    # 详情数据
    df_details = df[['代码', '名称', '最新价', '涨跌幅', '成交额', '总市值', '换手率']].copy()
    
    # 4. 保存结果
    output_dir = config.OUTPUT_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 保存汇总 (覆盖)
    summary_path = os.path.join(output_dir, "optical_module_summary.csv")
    df_summary.to_csv(summary_path, index=False, encoding='utf-8-sig')
    print(f"✅ 汇总数据已保存: {summary_path}")
    
    # 保存详情 (带时间戳)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    details_path = os.path.join(output_dir, f"optical_module_details_{timestamp}.csv")
    df_details.to_csv(details_path, index=False, encoding='utf-8-sig')
    print(f"✅ 详情数据已保存: {details_path}")
    
    # 5. 生成可视化报告
    print("\n正在生成可视化报告...")
    chart_path = generate_chart(df_details, output_dir)
    generate_excel_report(df_summary, df_details, chart_path, output_dir)
    
if __name__ == "__main__":
    main()
