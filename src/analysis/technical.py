"""
技术分析模块
"""

import pandas as pd
import numpy as np
from typing import List, Tuple


class TechnicalAnalyzer:
    """技术分析器"""
    
    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
        """
        计算移动平均线
        
        Args:
            df: 包含收盘价的DataFrame
            periods: 周期列表
            
        Returns:
            pd.DataFrame: 添加了MA列的DataFrame
        """
        result = df.copy()
        
        for period in periods:
            col_name = f'MA{period}'
            result[col_name] = result['收盘'].rolling(window=period).mean()
        
        return result
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, periods: List[int] = [12, 26]) -> pd.DataFrame:
        """
        计算指数移动平均线
        
        Args:
            df: 包含收盘价的DataFrame
            periods: 周期列表
            
        Returns:
            pd.DataFrame: 添加了EMA列的DataFrame
        """
        result = df.copy()
        
        for period in periods:
            col_name = f'EMA{period}'
            result[col_name] = result['收盘'].ewm(span=period, adjust=False).mean()
        
        return result
    
    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            df: 包含收盘价的DataFrame
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            pd.DataFrame: 添加了MACD相关列的DataFrame
        """
        result = df.copy()
        
        # 计算EMA
        ema_fast = result['收盘'].ewm(span=fast, adjust=False).mean()
        ema_slow = result['收盘'].ewm(span=slow, adjust=False).mean()
        
        # 计算DIF(MACD)
        result['DIF'] = ema_fast - ema_slow
        
        # 计算DEA(信号线)
        result['DEA'] = result['DIF'].ewm(span=signal, adjust=False).mean()
        
        # 计算MACD柱状图
        result['MACD'] = 2 * (result['DIF'] - result['DEA'])
        
        return result
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算RSI指标
        
        Args:
            df: 包含收盘价的DataFrame
            period: 周期
            
        Returns:
            pd.DataFrame: 添加了RSI列的DataFrame
        """
        result = df.copy()
        
        # 计算价格变化
        delta = result['收盘'].diff()
        
        # 分离涨跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均涨跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 计算RSI
        rs = avg_gain / avg_loss
        result['RSI'] = 100 - (100 / (1 + rs))
        
        return result
    
    @staticmethod
    def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """
        计算KDJ指标
        
        Args:
            df: 包含最高价、最低价、收盘价的DataFrame
            n: RSV周期
            m1: K值周期
            m2: D值周期
            
        Returns:
            pd.DataFrame: 添加了KDJ列的DataFrame
        """
        result = df.copy()
        
        # 计算RSV
        low_n = result['最低'].rolling(window=n).min()
        high_n = result['最高'].rolling(window=n).max()
        rsv = (result['收盘'] - low_n) / (high_n - low_n) * 100
        
        # 计算K值
        result['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
        
        # 计算D值
        result['D'] = result['K'].ewm(com=m2-1, adjust=False).mean()
        
        # 计算J值
        result['J'] = 3 * result['K'] - 2 * result['D']
        
        return result
    
    @staticmethod
    def calculate_boll(df: pd.DataFrame, period: int = 20, std_multiplier: float = 2) -> pd.DataFrame:
        """
        计算布林带指标
        
        Args:
            df: 包含收盘价的DataFrame
            period: 周期
            std_multiplier: 标准差倍数
            
        Returns:
            pd.DataFrame: 添加了布林带列的DataFrame
        """
        result = df.copy()
        
        # 计算中轨(MA)
        result['BOLL_MID'] = result['收盘'].rolling(window=period).mean()
        
        # 计算标准差
        std = result['收盘'].rolling(window=period).std()
        
        # 计算上轨和下轨
        result['BOLL_UP'] = result['BOLL_MID'] + std_multiplier * std
        result['BOLL_DOWN'] = result['BOLL_MID'] - std_multiplier * std
        
        return result
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有常用技术指标
        
        Args:
            df: 包含OHLC数据的DataFrame
            
        Returns:
            pd.DataFrame: 添加了所有指标的DataFrame
        """
        result = df.copy()
        
        # 移动平均线
        result = TechnicalAnalyzer.calculate_ma(result, [5, 10, 20, 60])
        
        # MACD
        result = TechnicalAnalyzer.calculate_macd(result)
        
        # RSI
        result = TechnicalAnalyzer.calculate_rsi(result)
        
        # KDJ
        result = TechnicalAnalyzer.calculate_kdj(result)
        
        # 布林带
        result = TechnicalAnalyzer.calculate_boll(result)
        
        return result
