"""
基础使用示例
"""

import sys
sys.path.append('..')

from src.data_fetch.stock_data import StockDataFetcher
from src.analysis.technical import TechnicalAnalyzer
from src.visualization.charts import ChartVisualizer, plot_stock_analysis


def main():
    """主函数"""
    
    # 1. 创建数据获取器
    print("=" * 50)
    print("AIQuant - 基于 AkShare 的金融分析工具")
    print("=" * 50)
    
    fetcher = StockDataFetcher()
    
    # 2. 获取股票数据
    print("\n正在获取平安银行(000001)的历史数据...")
    df = fetcher.get_stock_hist(
        symbol="000001",
        start_date="20240101",
        end_date="20241122",
        adjust="qfq"
    )
    
    if df.empty:
        print("获取数据失败!")
        return
    
    print(f"成功获取 {len(df)} 条数据")
    print("\n最近5天数据:")
    print(df.tail())
    
    # 3. 计算技术指标
    print("\n正在计算技术指标...")
    analyzer = TechnicalAnalyzer()
    df = analyzer.calculate_all_indicators(df)
    print("技术指标计算完成!")
    
    # 4. 数据分析
    print("\n" + "=" * 50)
    print("数据分析结果")
    print("=" * 50)
    
    latest = df.iloc[-1]
    print(f"\n最新价格: {latest['收盘']:.2f}")
    print(f"MA5: {latest['MA5']:.2f}")
    print(f"MA10: {latest['MA10']:.2f}")
    print(f"MA20: {latest['MA20']:.2f}")
    print(f"RSI: {latest['RSI']:.2f}")
    print(f"MACD: {latest['MACD']:.4f}")
    
    # 判断趋势
    if latest['收盘'] > latest['MA5'] > latest['MA10'] > latest['MA20']:
        print("\n趋势判断: 🔴 多头排列,强势上涨")
    elif latest['收盘'] < latest['MA5'] < latest['MA10'] < latest['MA20']:
        print("\n趋势判断: 🟢 空头排列,弱势下跌")
    else:
        print("\n趋势判断: 🟡 震荡整理")
    
    # 5. 数据可视化
    print("\n正在生成图表...")
    plot_stock_analysis(df.tail(60), title="平安银行")
    
    print("\n分析完成!")


if __name__ == "__main__":
    main()
