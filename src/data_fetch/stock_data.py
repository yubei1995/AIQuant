"""
股票数据获取模块
"""

import akshare as ak
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta


class StockDataFetcher:
    """股票数据获取器"""
    
    def __init__(self):
        """初始化"""
        pass

    def _add_market_prefix(self, symbol: str) -> str:
        """
        为股票代码添加市场前缀 (sh/sz/bj)
        
        Args:
            symbol: 股票代码 (e.g., "600519")
            
        Returns:
            str: 带前缀的代码 (e.g., "sh600519")
        """
        if not symbol[0].isdigit(): # 已经有前缀
            return symbol
            
        if symbol.startswith('6'):
            return f"sh{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz{symbol}"
        elif symbol.startswith('4') or symbol.startswith('8'):
            return f"bj{symbol}"
        return symbol
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表
        优先级: 新浪
        
        Returns:
            pd.DataFrame: 股票列表数据
        """
        # 1. 尝试新浪源
        try:
            # print("尝试新浪源获取股票列表...")
            df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                # 重命名以匹配通用格式
                df = df.rename(columns={
                    'code': '代码',
                    'name': '名称',
                    'trade': '最新价',
                    'changepercent': '涨跌幅',
                    'volume': '成交量',
                    'amount': '成交额',
                    'turnoverratio': '换手率',
                    'high': '最高',
                    'low': '最低',
                    'open': '今开',
                    'settlement': '昨收'
                })
                return df
        except Exception as e:
            print(f"新浪源获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_stock_realtime(self) -> pd.DataFrame:
        """
        获取A股实时行情
        优先级: 新浪 -> 东方财富
        
        Returns:
            pd.DataFrame: 实时行情数据
        """
        return self.get_stock_list()

    def get_stock_hist(
        self,
        symbol: str,
        period: str = "daily",
        start_date: str = "",
        end_date: str = "",
        adjust: str = ""
    ) -> pd.DataFrame:
        """
        获取个股历史数据
        优先级: 腾讯 -> 新浪 -> 东方财富
        
        Args:
            symbol: 股票代码
            period: 周期 daily(日), weekly(周), monthly(月)
            start_date: 开始日期 格式YYYYMMDD
            end_date: 结束日期 格式YYYYMMDD
            adjust: 复权类型 qfq(前复权), hfq(后复权), ""(不复权)
            
        Returns:
            pd.DataFrame: 历史数据
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
            
        # 1. 尝试腾讯源 (Tencent)
        try:
            # print(f"尝试腾讯源获取 {symbol}...")
            tx_symbol = self._add_market_prefix(symbol)
            df = ak.stock_zh_a_hist_tx(
                symbol=tx_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if df is not None and not df.empty:
                # 重命名列
                df = df.rename(columns={
                    'date': '日期',
                    'open': '开盘',
                    'close': '收盘',
                    'high': '最高',
                    'low': '最低',
                    'volume': '成交量',
                    'amount': '成交额'
                })
                # 确保日期格式
                if '日期' in df.columns:
                    df['日期'] = pd.to_datetime(df['日期'])
                    df = df.sort_values('日期')
                return df
        except Exception as e:
            print(f"腾讯源获取失败: {e}")

        # 2. 尝试新浪源 (Sina)
        try:
            # print(f"尝试新浪源获取 {symbol}...")
            sina_symbol = self._add_market_prefix(symbol)
            df = ak.stock_zh_a_daily(
                symbol=sina_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if df is not None and not df.empty:
                df = df.rename(columns={
                    'date': '日期',
                    'open': '开盘',
                    'high': '最高',
                    'low': '最低',
                    'close': '收盘',
                    'volume': '成交量'
                })
                if '日期' in df.columns:
                    df['日期'] = pd.to_datetime(df['日期'])
                    df = df.sort_values('日期')
                return df
        except Exception as e:
            print(f"新浪源获取失败: {e}")
            
        return pd.DataFrame()
    
    def get_stock_realtime(self) -> pd.DataFrame:
        """
        获取A股实时行情
        优先级: 新浪 -> 东方财富
        
        Returns:
            pd.DataFrame: 实时行情数据
        """
        return self.get_stock_list()
    
    def get_stock_info(self, symbol: str) -> dict:
        """
        获取个股基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 股票基本信息
        """
        try:
            # 尝试使用巨潮资讯源
            df = ak.stock_profile_cninfo(symbol=symbol)
            if df is not None and not df.empty:
                return df.iloc[0].to_dict()
        except Exception as e:
            print(f"获取股票 {symbol} 基本信息失败: {e}")
            return {}
    
    def get_financial_report(
        self,
        symbol: str,
        report_type: str = "资产负债表"
    ) -> pd.DataFrame:
        """
        获取财务报表
        
        Args:
            symbol: 股票代码
            report_type: 报表类型 资产负债表, 利润表, 现金流量表
            
        Returns:
            pd.DataFrame: 财务报表数据
        """
        try:
            # 尝试使用新浪源
            # 注意: 新浪源可能需要股票中文名称作为别名，这里简化处理，如果失败则返回空
            # 实际使用中可能需要先获取股票名称
            df = ak.stock_financial_report_sina(symbol=symbol, symbol_alias=symbol)
            return df
        except Exception as e:
            print(f"获取财务报表失败: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"获取股票 {symbol} {report_type}失败: {e}")
            return pd.DataFrame()


# 便捷函数
def get_stock_hist(
    symbol: str,
    start_date: str = "",
    end_date: str = "",
    period: str = "daily",
    adjust: str = ""
) -> pd.DataFrame:
    """
    快速获取股票历史数据
    
    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        period: 周期
        adjust: 复权类型
        
    Returns:
        pd.DataFrame: 历史数据
    """
    fetcher = StockDataFetcher()
    return fetcher.get_stock_hist(symbol, period, start_date, end_date, adjust)
