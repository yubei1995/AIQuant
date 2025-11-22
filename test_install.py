"""
测试 AkShare 安装和基本功能
"""

import akshare as ak

print("=" * 50)
print("AkShare 安装测试")
print("=" * 50)

# 1. 显示版本
print(f"\nAkShare 版本: {ak.__version__}")

# 2. 测试获取股票列表
print("\n正在测试获取A股股票列表...")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"✅ 成功! 获取到 {len(df)} 只股票")
    print("\n前5只股票:")
    print(df.head()[['代码', '名称', '最新价', '涨跌幅']])
except Exception as e:
    print(f"❌ 失败: {e}")

# 3. 测试获取历史数据
print("\n正在测试获取平安银行(000001)历史数据...")
try:
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", 
                            start_date="20241101", end_date="20241122")
    print(f"✅ 成功! 获取到 {len(df)} 条数据")
    print("\n最近5天数据:")
    print(df.tail()[['日期', '开盘', '收盘', '最高', '最低', '成交量']])
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "=" * 50)
print("测试完成!")
print("=" * 50)
