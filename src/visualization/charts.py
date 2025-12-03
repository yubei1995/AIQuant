"""
图表可视化模块
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
from typing import Optional, List
import warnings

warnings.filterwarnings('ignore')

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class ChartVisualizer:
    """图表可视化器"""
    
    def __init__(self, figsize: tuple = (15, 8), style: str = 'seaborn-v0_8-darkgrid'):
        """
        初始化
        
        Args:
            figsize: 图表大小
            style: 图表风格
        """
        self.figsize = figsize
        try:
            plt.style.use(style)
        except:
            plt.style.use('default')
            
        # 重新设置中文显示，防止被style覆盖
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
    
    def plot_candlestick(
        self,
        df: pd.DataFrame,
        title: str = "K线图",
        show_volume: bool = True,
        ma_periods: Optional[List[int]] = None,
        save_path: Optional[str] = None
    ):
        """
        绘制K线图
        
        Args:
            df: 包含OHLC数据的DataFrame
            title: 图表标题
            show_volume: 是否显示成交量
            ma_periods: 移动平均线周期列表
            save_path: 保存路径
        """
        if show_volume:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, 
                                           gridspec_kw={'height_ratios': [3, 1]})
        else:
            fig, ax1 = plt.subplots(figsize=self.figsize)
        
        # 绘制K线
        dates = df['日期'] if '日期' in df.columns else df.index
        # 转换为matplotlib date numbers
        if pd.api.types.is_datetime64_any_dtype(dates):
            date_nums = mdates.date2num(dates)
        else:
            date_nums = mdates.date2num(pd.to_datetime(dates))

        for i, (idx, row) in enumerate(df.iterrows()):
            date_num = date_nums[i]
            open_price = row['开盘']
            close_price = row['收盘']
            high_price = row['最高']
            low_price = row['最低']
            
            # 确定颜色(红涨绿跌)
            color = 'red' if close_price >= open_price else 'green'
            
            # 绘制影线
            ax1.plot([date_num, date_num], [low_price, high_price], color='black', linewidth=0.5)
            
            # 绘制实体
            height = abs(close_price - open_price)
            bottom = min(open_price, close_price)
            # 居中显示，宽度0.6，所以左边界是 date_num - 0.3
            rect = Rectangle((date_num - 0.3, bottom), width=0.6, height=height, 
                           facecolor=color, edgecolor='black', linewidth=0.5)
            ax1.add_patch(rect)
            
        ax1.xaxis_date()
        
        # 绘制移动平均线
        if ma_periods:
            for period in ma_periods:
                col_name = f'MA{period}'
                if col_name in df.columns:
                    ax1.plot(df['日期'] if '日期' in df.columns else df.index, 
                           df[col_name], label=col_name, linewidth=1.5)
        
        ax1.set_title(title, fontsize=16, fontweight='bold')
        ax1.set_ylabel('价格', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 绘制成交量
        if show_volume and '成交量' in df.columns:
            colors = ['red' if df.loc[idx, '收盘'] >= df.loc[idx, '开盘'] 
                     else 'green' for idx in df.index]
            ax2.bar(df['日期'] if '日期' in df.columns else df.index, 
                   df['成交量'], color=colors, alpha=0.6)
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.set_xlabel('日期', fontsize=12)
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_line(
        self,
        df: pd.DataFrame,
        columns: List[str],
        title: str = "趋势图",
        xlabel: str = "日期",
        ylabel: str = "价格",
        save_path: Optional[str] = None
    ):
        """
        绘制折线图
        
        Args:
            df: DataFrame
            columns: 要绘制的列名列表
            title: 图表标题
            xlabel: X轴标签
            ylabel: Y轴标签
            save_path: 保存路径
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        for col in columns:
            if col in df.columns:
                ax.plot(df['日期'] if '日期' in df.columns else df.index, 
                       df[col], label=col, linewidth=2)
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_macd(
        self,
        df: pd.DataFrame,
        title: str = "MACD指标",
        save_path: Optional[str] = None
    ):
        """
        绘制MACD指标图
        
        Args:
            df: 包含MACD数据的DataFrame
            title: 图表标题
            save_path: 保存路径
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # 绘制DIF和DEA
        ax.plot(df['日期'] if '日期' in df.columns else df.index, 
               df['DIF'], label='DIF', linewidth=2)
        ax.plot(df['日期'] if '日期' in df.columns else df.index, 
               df['DEA'], label='DEA', linewidth=2)
        
        # 绘制MACD柱状图
        colors = ['red' if val >= 0 else 'green' for val in df['MACD']]
        ax.bar(df['日期'] if '日期' in df.columns else df.index, 
              df['MACD'], color=colors, alpha=0.6, label='MACD')
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('MACD', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
    
    def plot_kdj(
        self,
        df: pd.DataFrame,
        title: str = "KDJ指标",
        save_path: Optional[str] = None
    ):
        """
        绘制KDJ指标图
        
        Args:
            df: 包含KDJ数据的DataFrame
            title: 图表标题
            save_path: 保存路径
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        ax.plot(df['日期'] if '日期' in df.columns else df.index, 
               df['K'], label='K', linewidth=2)
        ax.plot(df['日期'] if '日期' in df.columns else df.index, 
               df['D'], label='D', linewidth=2)
        ax.plot(df['日期'] if '日期' in df.columns else df.index, 
               df['J'], label='J', linewidth=2)
        
        # 添加超买超卖线
        ax.axhline(y=80, color='red', linestyle='--', linewidth=1, alpha=0.5)
        ax.axhline(y=20, color='green', linestyle='--', linewidth=1, alpha=0.5)
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('KDJ', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()


# 便捷函数
def plot_stock_analysis(df: pd.DataFrame, title: str = "股票分析"):
    """
    绘制综合分析图表
    
    Args:
        df: 包含完整数据的DataFrame
        title: 标题
    """
    visualizer = ChartVisualizer()
    
    # K线图和成交量
    visualizer.plot_candlestick(df, title=f"{title} - K线图", ma_periods=[5, 10, 20])
    
    # MACD
    if 'MACD' in df.columns:
        visualizer.plot_macd(df, title=f"{title} - MACD")
    
    # KDJ
    if 'K' in df.columns:
        visualizer.plot_kdj(df, title=f"{title} - KDJ")
