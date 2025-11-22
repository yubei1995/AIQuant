"""
辅助工具函数
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional


def save_to_csv(df: pd.DataFrame, filename: str, directory: str = "./data/") -> bool:
    """
    保存DataFrame到CSV文件
    
    Args:
        df: DataFrame
        filename: 文件名
        directory: 目录路径
        
    Returns:
        bool: 是否保存成功
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        filepath = Path(directory) / filename
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"数据已保存到: {filepath}")
        return True
    except Exception as e:
        print(f"保存文件失败: {e}")
        return False


def load_from_csv(filename: str, directory: str = "./data/") -> Optional[pd.DataFrame]:
    """
    从CSV文件加载DataFrame
    
    Args:
        filename: 文件名
        directory: 目录路径
        
    Returns:
        pd.DataFrame: 加载的数据,失败返回None
    """
    try:
        filepath = Path(directory) / filename
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        print(f"数据已加载: {filepath}")
        return df
    except Exception as e:
        print(f"加载文件失败: {e}")
        return None


def format_date(date_str: str, input_format: str = "%Y%m%d", 
                output_format: str = "%Y-%m-%d") -> str:
    """
    格式化日期字符串
    
    Args:
        date_str: 日期字符串
        input_format: 输入格式
        output_format: 输出格式
        
    Returns:
        str: 格式化后的日期字符串
    """
    try:
        date_obj = datetime.strptime(date_str, input_format)
        return date_obj.strftime(output_format)
    except Exception as e:
        print(f"日期格式化失败: {e}")
        return date_str


def get_trading_days_ago(days: int) -> str:
    """
    获取N个交易日前的日期
    
    Args:
        days: 天数
        
    Returns:
        str: 日期字符串 格式YYYYMMDD
    """
    from datetime import timedelta
    date = datetime.now() - timedelta(days=days)
    return date.strftime("%Y%m%d")


def get_today() -> str:
    """
    获取今天的日期
    
    Returns:
        str: 日期字符串 格式YYYYMMDD
    """
    return datetime.now().strftime("%Y%m%d")


def calculate_return(start_price: float, end_price: float) -> float:
    """
    计算收益率
    
    Args:
        start_price: 起始价格
        end_price: 结束价格
        
    Returns:
        float: 收益率(百分比)
    """
    return ((end_price - start_price) / start_price) * 100


def calculate_volatility(prices: pd.Series) -> float:
    """
    计算价格波动率(标准差)
    
    Args:
        prices: 价格序列
        
    Returns:
        float: 波动率
    """
    returns = prices.pct_change().dropna()
    return returns.std()
