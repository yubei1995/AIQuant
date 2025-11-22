"""
查询新易盛的行业信息
"""
import akshare as ak
import pandas as pd

# 设置显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_rows', None)

print("=" * 60)
print("新易盛(300502) 详细信息")
print("=" * 60)

# 1. 获取个股信息
print("\n【基本信息】")
try:
    info_df = ak.stock_individual_info_em(symbol="300502")
    for idx, row in info_df.iterrows():
        print(f"{row['item']:.<20} {row['value']}")
except Exception as e:
    print(f"获取失败: {e}")

# 2. 获取行业板块信息
print("\n【所属板块】")
print("行业: 通信设备")

# 3. 获取财务指标
print("\n【财务指标】")
try:
    # 获取主要财务指标
    finance_df = ak.stock_financial_analysis_indicator(symbol="300502")
    if not finance_df.empty:
        latest = finance_df.iloc[0]
        print(f"报告期: {latest['报告日']}")
        print(f"净资产收益率: {latest.get('净资产收益率', 'N/A')}")
        print(f"总资产收益率: {latest.get('总资产收益率', 'N/A')}")
        print(f"销售毛利率: {latest.get('销售毛利率', 'N/A')}")
        print(f"销售净利率: {latest.get('销售净利率', 'N/A')}")
except Exception as e:
    print(f"获取财务指标失败: {e}")

# 4. 获取同行业对比
print("\n【同行业公司对比 - 通信设备】")
try:
    import time
    time.sleep(2)  # 延迟避免请求过快
    industry_cons = ak.stock_board_industry_cons_em(symbol="通信设备")
    
    # 筛选几个知名的通信设备公司
    target_codes = ['300502', '002583', '000063', '600498', '002396']
    result = industry_cons[industry_cons['代码'].isin(target_codes)]
    
    if not result.empty:
        print(result[['代码', '名称', '最新价', '涨跌幅', '市盈率-动态', '市净率']].to_string(index=False))
    else:
        print("未能获取同行业公司数据")
except Exception as e:
    print(f"同行业对比获取失败: {e}")

print("\n" + "=" * 60)
