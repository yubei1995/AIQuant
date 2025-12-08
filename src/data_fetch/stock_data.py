"""
股票数据获取模块
"""

import akshare as ak
import pandas as pd
import requests
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
        if symbol.startswith('4') or symbol.startswith('8'):
            return f"bj{symbol}"
        return symbol
    
    def get_stock_realtime_batch(self, symbol_list: list) -> pd.DataFrame:
        """
        批量获取指定股票的实时行情（腾讯源）
        
        Args:
            symbol_list: 股票代码列表 (e.g., ["600519", "000001"])
            
        Returns:
            pd.DataFrame: 包含实时行情的DataFrame
        """
        if not symbol_list:
            return pd.DataFrame()
            
        # 构建请求URL
        # 腾讯接口格式: http://qt.gtimg.cn/q=sh600519,sz000001
        prefixed_symbols = [self._add_market_prefix(s) for s in symbol_list]
        # 腾讯接口一次请求太多可能会失败，建议分批，这里假设列表不长
        # 如果列表很长，可以分批请求
        
        all_data = []
        batch_size = 50
        for i in range(0, len(prefixed_symbols), batch_size):
            batch = prefixed_symbols[i:i+batch_size]
            url = f"http://qt.gtimg.cn/q={','.join(batch)}"
            
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    print(f"腾讯源请求失败: {resp.status_code}")
                    continue
                    
                # 解析数据
                lines = resp.text.strip().split(';')
                for line in lines:
                    if not line.strip():
                        continue
                    
                    # line format: v_sh600519="1~贵州茅台~600519~..."
                    parts = line.split('=')
                    if len(parts) < 2:
                        continue
                        
                    vals = parts[1].strip('"').split('~')
                    if len(vals) < 46: # 确保有足够字段
                        continue
                        
                    # 提取字段
                    # 1:名称, 2:代码, 3:最新价, 32:涨跌幅(%), 36:成交量(手), 37:成交额(万), 44:流通市值(亿), 45:总市值(亿)
                    try:
                        item = {
                            '代码': vals[2],
                            '名称': vals[1],
                            '最新价': float(vals[3]),
                            '涨跌幅': float(vals[32]),
                            '成交量': float(vals[36]), # 腾讯返回手
                            '成交额': float(vals[37]) * 10000, # 腾讯返回万，转为元
                            '流通市值': float(vals[44]) * 100000000 if vals[44] else 0, # 亿 -> 元
                            '总市值': float(vals[45]) * 100000000 if vals[45] else 0, # 亿 -> 元
                            '换手率': float(vals[38]) if vals[38] else 0
                        }
                        all_data.append(item)
                    except (ValueError, IndexError) as e:
                        # print(f"解析股票数据出错 {vals[2]}: {e}")
                        continue
            except Exception as e:
                print(f"批量获取实时行情失败: {e}")
                
        return pd.DataFrame(all_data)

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
                    'mktcap': '总市值',  # 新浪源包含 mktcap 字段
                    'nmc': '流通市值',     # 新浪源包含 nmc 字段
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

    def get_stock_realtime_batch(self, symbols: list) -> pd.DataFrame:
        """
        批量获取股票实时行情 (腾讯源)
        
        Args:
            symbols: 股票代码列表 (e.g., ["600519", "000001"])
            
        Returns:
            pd.DataFrame: 实时行情数据
        """
        if not symbols:
            return pd.DataFrame()
            
        # 添加前缀
        prefixed_symbols = [self._add_market_prefix(s) for s in symbols]
        
        # 分批处理，每批80个
        batch_size = 80
        results = []
        
        for i in range(0, len(prefixed_symbols), batch_size):
            batch = prefixed_symbols[i:i+batch_size]
            query_str = ",".join(batch)
            url = f"http://qt.gtimg.cn/q={query_str}"
            
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    # 解析数据
                    lines = resp.text.strip().split(';')
                    for line in lines:
                        if not line.strip():
                            continue
                        # v_sh600519="1~贵州茅台~600519~..."
                        try:
                            content = line.split('="')[1].strip('"')
                            parts = content.split('~')
                            if len(parts) > 45:
                                data = {
                                    '代码': parts[2],
                                    '名称': parts[1],
                                    '最新价': float(parts[3]),
                                    '涨跌幅': float(parts[32]),
                                    '成交量': float(parts[6]), # 手
                                    '成交额': float(parts[37]) * 10000, # 万 -> 元
                                    '总市值': float(parts[45]) * 100000000, # 亿 -> 元
                                    '换手率': float(parts[38]) if parts[38] else 0.0,
                                    '最高': float(parts[33]),
                                    '最低': float(parts[34]),
                                    '今开': float(parts[5]),
                                    '昨收': float(parts[4])
                                }
                                results.append(data)
                        except Exception as e:
                            continue
            except Exception as e:
                print(f"Batch fetch error: {e}")
                
        return pd.DataFrame(results)

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
                # 注意：腾讯源返回的 amount 其实是成交量(手/股)，而不是成交额
                # 腾讯源似乎没有返回成交额字段，或者字段名不同
                df = df.rename(columns={
                    'date': '日期',
                    'open': '开盘',
                    'close': '收盘',
                    'high': '最高',
                    'low': '最低',
                    'amount': '成交量'  # 修正：amount 映射为 成交量
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
                # 统一单位：新浪源返回的是股，转换为手(除以100)
                # 腾讯源返回的是手，保持一致
                if '成交量' in df.columns:
                    df['成交量'] = df['成交量'] / 100
                    
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
