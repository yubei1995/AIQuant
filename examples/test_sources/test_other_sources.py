"""
测试除了东方财富(EastMoney)和新浪(Sina)之外的其他数据源
主要测试: 腾讯(Tencent), 网易(NetEase), 搜狐(Sohu) 等
"""
import akshare as ak
import pandas as pd
import time
from pathlib import Path

# 确保输出目录存在
# 修改为当前脚本所在目录下的 data 文件夹
output_dir = Path(__file__).parent / "data"
output_dir.mkdir(parents=True, exist_ok=True)

def test_source(name, func, filename, **kwargs):
    print(f"\n{'='*50}")
    print(f"测试平台: {name}")
    print(f"函数: {func.__name__}")
    try:
        start_time = time.time()
        df = func(**kwargs)
        duration = time.time() - start_time
        
        if df is not None and not df.empty:
            print(f"✅ 成功! 耗时: {duration:.2f}秒")
            print(f"数据形状: {df.shape}")
            print("前3行数据:")
            print(df.head(3))
            
            # 保存为TXT文件
            file_path = output_dir / f"{filename}.txt"
            df.to_csv(file_path, sep='\t', index=False)
            print(f"已保存至: {file_path}")
            return True
        else:
            print("⚠️ 成功但返回空数据")
            return False
    except Exception as e:
        print(f"❌ 失败: {e}")
        return False

print("开始多平台数据源可用性测试...")

# 1. 腾讯财经 (Tencent) - 历史数据
print("\n【1. 腾讯财经 (Tencent)】")
test_source(
    "腾讯财经-个股历史", 
    ak.stock_zh_a_hist_tx, 
    "tencent_history_000001",
    symbol="sz000001", 
    start_date="20240101", 
    end_date="20240110",
    adjust="qfq"
)

# 2. 腾讯财经 (Tencent) - 指数数据
print("\n【2. 腾讯财经 (Tencent) - 指数】")
# 腾讯指数接口可能比较慢，这里只获取少量或跳过如果太慢
# 为了演示，我们尝试获取一个
try:
    test_source(
        "腾讯财经-指数历史",
        ak.stock_zh_index_daily_tx,
        "tencent_index_sh000001",
        symbol="sh000001"
    )
except Exception as e:
    print(f"腾讯指数获取跳过: {e}")

# 3. 雪球 (Snowball) - 实时行情
print("\n【3. 雪球 (Snowball)】")
test_source(
    "雪球-个股实时",
    ak.stock_individual_spot_xq,
    "snowball_spot_600519",
    symbol="SH600519"
)

# 4. 百度 (Baidu) - 估值数据
print("\n【4. 百度股市通 (Baidu)】")
test_source(
    "百度-个股估值",
    ak.stock_zh_valuation_baidu,
    "baidu_valuation_600519",
    symbol="600519"
)

