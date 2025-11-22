"""
白酒行业分析 - 通过逐个查询主要公司
"""
import akshare as ak
import pandas as pd
import time

# 白酒行业主要公司
companies = {
    '600519': '贵州茅台',
    '000858': '五粮液',
    '000568': '泸州老窖',
    '002304': '洋河股份',
    '600809': '山西汾酒',
    '000799': '酒鬼酒',
    '603369': '今世缘',
    '000596': '古井贡酒',
    '600702': '舍得酒业',
    '603589': '口子窖'
}

print("=" * 80)
print("白酒行业主要公司数据分析")
print("=" * 80)

all_data = []

print(f"\n正在获取 {len(companies)} 家白酒公司的数据...\n")

for code, name in companies.items():
    try:
        # 获取最近一天的数据
        df = ak.stock_zh_a_hist(
            symbol=code,
            period='daily',
            start_date='20251120',
            end_date='20251122',
            adjust='qfq'
        )
        
        if not df.empty:
            latest = df.iloc[-1]
            
            # 获取基本信息
            info = ak.stock_individual_info_em(symbol=code)
            total_value = float(info[info['item']=='总市值']['value'].values[0])
            liutong_value = float(info[info['item']=='流通市值']['value'].values[0])
            
            data = {
                '代码': code,
                '名称': name,
                '最新价': latest['收盘'],
                '涨跌幅': latest['涨跌幅'],
                '涨跌额': latest['涨跌额'],
                '成交量': latest['成交量'],
                '成交额': latest['成交额'],
                '换手率': latest['换手率'],
                '振幅': latest['振幅'],
                '总市值(亿)': round(total_value / 100000000, 2),
                '流通市值(亿)': round(liutong_value / 100000000, 2)
            }
            all_data.append(data)
            print(f"✓ {name}({code}): {latest['收盘']:.2f}元, 涨跌幅 {latest['涨跌幅']:.2f}%")
        
        time.sleep(1)  # 避免请求过快
        
    except Exception as e:
        print(f"✗ {name}({code}): 获取失败 - {e}")

# 创建DataFrame
if all_data:
    industry_df = pd.DataFrame(all_data)
    
    print("\n" + "=" * 80)
    print("【一、白酒行业整体数据】")
    print("=" * 80)
    
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print(f"\n成功获取 {len(industry_df)} 家白酒公司数据")
    print("\n详细数据:")
    print(industry_df.to_string(index=False))
    
    # 统计分析
    print("\n" + "=" * 80)
    print("【二、行业统计分析】")
    print("=" * 80)
    
    print(f"\n涨跌分布:")
    up_count = len(industry_df[industry_df['涨跌幅'] > 0])
    down_count = len(industry_df[industry_df['涨跌幅'] < 0])
    flat_count = len(industry_df[industry_df['涨跌幅'] == 0])
    print(f"  上涨: {up_count} 家 ({up_count/len(industry_df)*100:.1f}%)")
    print(f"  下跌: {down_count} 家 ({down_count/len(industry_df)*100:.1f}%)")
    print(f"  平盘: {flat_count} 家 ({flat_count/len(industry_df)*100:.1f}%)")
    
    print(f"\n涨跌幅统计:")
    print(f"  平均涨跌幅: {industry_df['涨跌幅'].mean():.2f}%")
    print(f"  最大涨幅: {industry_df['涨跌幅'].max():.2f}% ({industry_df.loc[industry_df['涨跌幅'].idxmax(), '名称']})")
    print(f"  最大跌幅: {industry_df['涨跌幅'].min():.2f}% ({industry_df.loc[industry_df['涨跌幅'].idxmin(), '名称']})")
    
    print(f"\n市值统计:")
    total_market_cap = industry_df['总市值(亿)'].sum()
    print(f"  行业总市值: {total_market_cap:,.2f} 亿元")
    print(f"  平均市值: {industry_df['总市值(亿)'].mean():,.2f} 亿元")
    print(f"  最大市值: {industry_df['总市值(亿)'].max():,.2f} 亿元 ({industry_df.loc[industry_df['总市值(亿)'].idxmax(), '名称']})")
    
    print(f"\n成交活跃度:")
    print(f"  平均换手率: {industry_df['换手率'].mean():.2f}%")
    print(f"  平均振幅: {industry_df['振幅'].mean():.2f}%")
    print(f"  总成交额: {industry_df['成交额'].sum()/100000000:,.2f} 亿元")
    
    # 排名
    print("\n" + "=" * 80)
    print("【三、涨幅排行榜】")
    print("=" * 80)
    sorted_df = industry_df.sort_values('涨跌幅', ascending=False)
    print(sorted_df[['代码', '名称', '最新价', '涨跌幅', '涨跌额', '换手率']].to_string(index=False))
    
    print("\n" + "=" * 80)
    print("【四、市值排行榜】")
    print("=" * 80)
    sorted_by_cap = industry_df.sort_values('总市值(亿)', ascending=False)
    print(sorted_by_cap[['代码', '名称', '最新价', '总市值(亿)', '流通市值(亿)', '涨跌幅']].to_string(index=False))
    
    print("\n" + "=" * 80)
    print("【五、成交活跃排行】")
    print("=" * 80)
    sorted_by_amount = industry_df.sort_values('成交额', ascending=False)
    print(sorted_by_amount[['代码', '名称', '成交额', '换手率', '涨跌幅']].to_string(index=False))
    
    # 龙头分析
    print("\n" + "=" * 80)
    print("【六、行业龙头对比 - 茅台 vs 五粮液】")
    print("=" * 80)
    
    maotai = industry_df[industry_df['代码'] == '600519']
    wuliangye = industry_df[industry_df['代码'] == '000858']
    
    if not maotai.empty and not wuliangye.empty:
        mt = maotai.iloc[0]
        wly = wuliangye.iloc[0]
        
        print(f"\n贵州茅台(600519):")
        print(f"  最新价: {mt['最新价']:.2f}元")
        print(f"  涨跌幅: {mt['涨跌幅']:.2f}%")
        print(f"  总市值: {mt['总市值(亿)']:,.2f}亿元")
        print(f"  成交额: {mt['成交额']/100000000:.2f}亿元")
        print(f"  换手率: {mt['换手率']:.2f}%")
        
        print(f"\n五粮液(000858):")
        print(f"  最新价: {wly['最新价']:.2f}元")
        print(f"  涨跌幅: {wly['涨跌幅']:.2f}%")
        print(f"  总市值: {wly['总市值(亿)']:,.2f}亿元")
        print(f"  成交额: {wly['成交额']/100000000:.2f}亿元")
        print(f"  换手率: {wly['换手率']:.2f}%")
        
        print(f"\n市值差距: {mt['总市值(亿)'] - wly['总市值(亿)']:,.2f}亿元")
        print(f"市值比例: 茅台/五粮液 = {mt['总市值(亿)']/wly['总市值(亿)']:.2f}倍")
    
    # 行业洞察
    print("\n" + "=" * 80)
    print("【七、行业洞察】")
    print("=" * 80)
    
    print("\n白酒行业特点:")
    print("  • 消费属性强，受经济周期影响")
    print("  • 高端白酒(茅台、五粮液)具有品牌护城河")
    print("  • 区域酒企(汾酒、古井贡)具有地域优势")
    print("  • 行业集中度高，龙头效应明显")
    
    if industry_df['涨跌幅'].mean() > 1:
        print("\n今日行业表现: 🔴 整体上涨，市场情绪乐观")
    elif industry_df['涨跌幅'].mean() < -1:
        print("\n今日行业表现: 🟢 整体下跌，市场情绪谨慎")
    else:
        print("\n今日行业表现: 🟡 震荡整理，观望情绪较重")
    
else:
    print("\n❌ 未能获取任何数据")
    print("可能原因:")
    print("  1. 网络连接问题")
    print("  2. API访问限制")
    print("  3. 建议稍后重试或使用VPN")

print("\n" + "=" * 80)
print("分析完成")
print("=" * 80)
