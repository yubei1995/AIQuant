"""
新易盛(300502)详细分析报告
"""
import akshare as ak
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

print("=" * 70)
print("新易盛(300502) 详细分析报告")
print("=" * 70)

# 1. 基本信息
print("\n【一、基本信息】")
info_df = ak.stock_individual_info_em(symbol="300502")
for idx, row in info_df.iterrows():
    print(f"  {row['item']:.<25} {row['value']}")

# 2. 最新行情
print("\n【二、最近20日行情】")
df = ak.stock_zh_a_hist(
    symbol='300502', 
    period='daily', 
    start_date='20251025', 
    end_date='20251122', 
    adjust='qfq'
)

print(f"  时间范围: {df.iloc[0]['日期']} 至 {df.iloc[-1]['日期']}")
print(f"  期初价格: {df.iloc[0]['收盘']:.2f} 元")
print(f"  期末价格: {df.iloc[-1]['收盘']:.2f} 元")
print(f"  期间涨幅: {((df.iloc[-1]['收盘']/df.iloc[0]['收盘']-1)*100):.2f}%")
print(f"  最高价格: {df['最高'].max():.2f} 元")
print(f"  最低价格: {df['最低'].min():.2f} 元")
print(f"  平均成交量: {df['成交量'].mean():.0f} 手")

# 3. 技术分析
print("\n【三、技术指标】")
# 计算5日和10日均线
df['MA5'] = df['收盘'].rolling(window=5).mean()
df['MA10'] = df['收盘'].rolling(window=10).mean()

latest = df.iloc[-1]
print(f"  最新收盘价: {latest['收盘']:.2f} 元")
print(f"  5日均线: {latest['MA5']:.2f} 元")
print(f"  10日均线: {latest['MA10']:.2f} 元")

if latest['收盘'] > latest['MA5'] > latest['MA10']:
    trend = "多头排列 ↗️"
elif latest['收盘'] < latest['MA5'] < latest['MA10']:
    trend = "空头排列 ↘️"
else:
    trend = "震荡整理 ↔️"
print(f"  趋势判断: {trend}")

# 4. 近期表现
print("\n【四、最近5日表现】")
print(df[['日期', '收盘', '涨跌幅', '成交量', '换手率']].tail(5).to_string(index=False))

# 5. 行业定位
print("\n【五、行业定位】")
# 从API获取的行业信息
industry = info_df[info_df['item'] == '行业']['value'].values[0]
print(f"  所属行业(API数据): {industry}")
print("\n  补充信息(非API数据,仅供参考):")
print("    - 业务方向: 光模块、光通信、数据中心互连")
print("    - 市场特点: 通信设备制造业")
print("    - 应用领域: 数据中心、5G通信")

# 6. 风险提示
print("\n【六、投资提示】")
change_from_high = ((latest['收盘'] - df['最高'].max()) / df['最高'].max()) * 100
print(f"  距离近期高点: {change_from_high:.2f}%")

if abs(latest['涨跌幅']) > 5:
    print(f"  ⚠️  最新交易日波动较大({latest['涨跌幅']:.2f}%),注意风险")

if latest['收盘'] < latest['MA10']:
    print("  ⚠️  价格低于10日均线,短期趋势偏弱")

print("\n" + "=" * 70)
print("注: 数据来源于公开市场,仅供参考,不构成投资建议")
print("=" * 70)
