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
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表
        
        Returns:
            pd.DataFrame: 股票列表数据
        """
        try:
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
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
        
        Args:
            symbol: 股票代码
            period: 周期 daily(日), weekly(周), monthly(月)
            start_date: 开始日期 格式YYYYMMDD
            end_date: 结束日期 格式YYYYMMDD
            adjust: 复权类型 qfq(前复权), hfq(后复权), ""(不复权)
            
        Returns:
            pd.DataFrame: 历史数据
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            # 将日期列转换为datetime类型
            if '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.sort_values('日期')
            
            return df
        except Exception as e:
            print(f"获取股票 {symbol} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_realtime(self) -> pd.DataFrame:
        """
        获取A股实时行情
        
        Returns:
            pd.DataFrame: 实时行情数据
        """
        try:
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_stock_info(self, symbol: str) -> dict:
        """
        获取个股基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 股票基本信息
        """
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            return df.set_index('item')['value'].to_dict()
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
            if report_type == "资产负债表":
                df = ak.stock_balance_sheet_by_report_em(symbol=symbol)
            elif report_type == "利润表":
                df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
            elif report_type == "现金流量表":
                df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
            else:
                print(f"不支持的报表类型: {report_type}")
                return pd.DataFrame()
            
            return df
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
