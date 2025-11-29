import pandas as pd
import numpy as np

class SectorAnalyzer:
    """
    通用板块分析器
    用于分析一组股票的整体表现、相关性和强弱
    """
    def __init__(self, stock_data_dict):
        """
        :param stock_data_dict: 字典, key为股票代码, value为DataFrame(包含'收盘'列)
        """
        self.stock_data = stock_data_dict
        self.close_prices = self._align_data()

    def _align_data(self):
        """将所有股票的收盘价对齐到一个DataFrame"""
        df_list = []
        for code, df in self.stock_data.items():
            if df is not None and not df.empty:
                # 确保日期是索引
                if '日期' in df.columns:
                    temp_df = df.set_index('日期')[['收盘']].rename(columns={'收盘': code})
                else:
                    temp_df = df[['收盘']].rename(columns={'收盘': code})
                df_list.append(temp_df)
        
        if not df_list:
            return pd.DataFrame()
            
        # 合并并按日期排序
        aligned_df = pd.concat(df_list, axis=1).sort_index()
        return aligned_df

    def calculate_correlation(self):
        """计算收益率相关性矩阵"""
        if self.close_prices.empty:
            return None
        # 计算日收益率
        returns = self.close_prices.pct_change().dropna()
        # 计算相关性
        return returns.corr()

    def calculate_sector_index(self, method='equal'):
        """
        计算板块指数
        :param method: 'equal' (等权), 'price' (价格平均 - 不推荐), 'market_cap' (需额外数据)
        """
        if self.close_prices.empty:
            return None
            
        if method == 'equal':
            # 归一化：以第一天为100点
            normalized = self.close_prices / self.close_prices.iloc[0] * 100
            # 计算平均值
            index_series = normalized.mean(axis=1)
            return index_series
        
        return None

    def get_top_performers(self, period_days=20):
        """获取近期表现最好的股票"""
        if self.close_prices.empty:
            return None
            
        # 计算区间涨跌幅
        start_price = self.close_prices.iloc[-period_days]
        end_price = self.close_prices.iloc[-1]
        
        change = (end_price - start_price) / start_price * 100
        return change.sort_values(ascending=False)
