"""
测试 AkShare 安装和基本功能
"""

import akshare as ak

print("=" * 50)
print("AkShare 安装测试")
print("=" * 50)

# 1. 显示版本
print(f"\nAkShare 版本: {ak.__version__}")

# 2. 测试获取股票列表 (优先使用新浪源)
print("\n正在测试获取A股股票列表(新浪源)...")
try:
    df = ak.stock_zh_a_spot()
    print(f"✅ 成功! 获取到 {len(df)} 只股票")
    print("\n前5只股票:")
    # 新浪源列名: code, name, trade, changepercent
    print(df[['code', 'name', 'trade', 'changepercent']].head())
except Exception as e:
    print(f"❌ 新浪源失败: {e}")

# 3. 测试获取历史数据 (优先使用腾讯源)
print("\n正在测试获取平安银行(000001)历史数据(腾讯源)...")
try:
    # 腾讯源需要 sz/sh 前缀
    df = ak.stock_zh_a_hist_tx(symbol="sz000001", start_date="20241101", end_date="20241122")
    print(f"✅ 成功! 获取到 {len(df)} 条数据")
    print("\n最近5天数据:")
    print(df.tail())
except Exception as e:
    print(f"❌ 腾讯源失败: {e}")
    print("尝试新浪源...")
    try:
        df = ak.stock_zh_a_daily(symbol="sz000001", start_date="20241101", end_date="20241122")
        print(f"✅ 成功! 获取到 {len(df)} 条数据")
        print(df.tail())
    except Exception as e2:
        print(f"❌ 新浪源失败: {e2}")

print("\n" + "=" * 50)
print("测试完成!")
print("=" * 50)
