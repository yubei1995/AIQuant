"""
光模块板块分析主程序
"""
import sys
import os
from pathlib import Path
import time

# 添加项目根目录到路径，以便导入src模块
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

import pandas as pd
import matplotlib.pyplot as plt
from src.data_fetch.stock_data import StockDataFetcher
from src.analysis.sector import SectorAnalyzer
from src.visualization.charts import ChartVisualizer
from examples.Optical_Module import config

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def main():
    print("=" * 50)
    print("开始光模块(CPO)板块分析")
    print("=" * 50)

    # 1. 初始化
    fetcher = StockDataFetcher()
    stock_data = {}
    
    # 2. 获取数据
    print(f"正在获取 {len(config.ALL_STOCKS)} 只股票的历史数据...")
    for code, name in config.ALL_STOCKS.items():
        print(f"  - 获取 {name} ({code})...")
        try:
            # 获取2024年至今的数据
            df = fetcher.get_stock_hist(code, start_date=config.START_DATE, end_date="20251231")
            if df is not None and not df.empty:
                stock_data[code] = df
            time.sleep(1) # 避免请求过快
        except Exception as e:
            print(f"    获取失败: {e}")

    if not stock_data:
        print("❌ 未获取到任何数据，程序结束")
        return

    # 3. 板块分析
    analyzer = SectorAnalyzer(stock_data)
    
    # 3.1 计算相关性
    print("\n【相关性分析】")
    corr_matrix = analyzer.calculate_correlation()
    print("收益率相关性矩阵(前5只):")
    # 将代码替换为名称以便阅读
    renamed_corr = corr_matrix.rename(index=config.ALL_STOCKS, columns=config.ALL_STOCKS)
    print(renamed_corr.iloc[:5, :5])

    # 3.2 板块指数
    print("\n【板块指数】")
    sector_index = analyzer.calculate_sector_index(method='equal')
    print(f"当前板块等权指数点位: {sector_index.iloc[-1]:.2f}")
    print(f"今年以来涨跌幅: {(sector_index.iloc[-1] - 100):.2f}%")

    # 3.3 领涨个股
    print("\n【近20交易日领涨个股】")
    top_performers = analyzer.get_top_performers(period_days=20)
    for code, change in top_performers.head(5).items():
        name = config.ALL_STOCKS.get(code, code)
        print(f"  {name}: {change:+.2f}%")

    # 4. 简单可视化
    print("\n正在绘制板块走势图...")
    plt.figure(figsize=(12, 6))
    
    # 绘制指数
    plt.plot(sector_index.index, sector_index.values, label='光模块等权指数', linewidth=2, color='red')
    
    # 绘制核心龙头
    for code in config.CORE_STOCKS:
        if code in stock_data:
            df = stock_data[code].set_index('日期')
            # 归一化
            norm_price = df['收盘'] / df['收盘'].iloc[0] * 100
            plt.plot(norm_price.index, norm_price.values, label=config.CORE_STOCKS[code], alpha=0.6, linestyle='--')

    plt.title('光模块板块 vs 核心龙头走势 (2024至今)')
    plt.xlabel('日期')
    plt.ylabel('归一化净值 (基准=100)')
    plt.legend()
    plt.grid(True)
    
    # 确保输出目录存在
    Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    output_img = os.path.join(config.OUTPUT_DIR, "sector_trend.png")
    plt.savefig(output_img)
    print(f"✅ 图表已保存至: {output_img}")
    # plt.show() # 如果在本地运行可以取消注释

    # 5. 个股详细K线图 (使用 ChartVisualizer)
    print("\n正在绘制龙头股K线图...")
    visualizer = ChartVisualizer()
    
    # 选取一只龙头股，例如中际旭创 (300308)
    target_code = "300308"
    if target_code in stock_data:
        target_name = config.ALL_STOCKS.get(target_code, target_code)
        kline_output = os.path.join(config.OUTPUT_DIR, f"{target_code}_kline.png")
        
        # 确保数据按日期排序
        df_plot = stock_data[target_code].sort_values('日期').reset_index(drop=True)
        
        try:
            visualizer.plot_candlestick(
                df_plot,
                title=f"{target_name} ({target_code}) 日K线走势",
                show_volume=True,
                save_path=kline_output
            )
            print(f"✅ 个股K线图已保存至: {kline_output}")
        except Exception as e:
            print(f"❌ 绘制K线图失败: {e}")
    # plt.show() # 如果在本地运行可以取消注释

if __name__ == "__main__":
    main()
