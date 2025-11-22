"""
通过逐个查询主要公司来构建通信设备行业数据
"""
import akshare as ak
import pandas as pd
import time

# 通信设备行业主要公司
companies = {
    '300502': '新易盛',
    '300308': '中际旭创', 
    '000063': '中兴通讯',
    '600498': '烽火通信',
    '002583': '海能达',
    '002396': '星网锐捷',
    '603322': '超讯通信',
    '002544': '杰赛科技',
    '300136': '信维通信',
    '300597': '吉大通信'
}

print("=" * 80)
print("通信设备行业主要公司数据分析")
print("=" * 80)

all_data = []

print(f"\n正在获取 {len(companies)} 家公司的数据...\n")

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
            
            data = {
                '代码': code,
                '名称': name,
                '最新价': latest['收盘'],
                '涨跌幅': latest['涨跌幅'],
                '成交量': latest['成交量'],
                '成交额': latest['成交额'],
                '换手率': latest['换手率'],
                '总市值': total_value / 100000000,  # 转换为亿元
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
    print("【一、行业整体数据】")
    print("=" * 80)
    
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    
    print(f"\n成功获取 {len(industry_df)} 家公司数据")
    print("\n详细数据:")
    print(industry_df.to_string(index=False))
    
    # 统计分析
    print("\n" + "=" * 80)
    print("【二、统计分析】")
    print("=" * 80)
    
    print(f"\n涨跌分布:")
    up_count = len(industry_df[industry_df['涨跌幅'] > 0])
    down_count = len(industry_df[industry_df['涨跌幅'] < 0])
    print(f"  上涨: {up_count} 家 ({up_count/len(industry_df)*100:.1f}%)")
    print(f"  下跌: {down_count} 家 ({down_count/len(industry_df)*100:.1f}%)")
    
    print(f"\n涨跌幅:")
    print(f"  平均: {industry_df['涨跌幅'].mean():.2f}%")
    print(f"  最高: {industry_df['涨跌幅'].max():.2f}% ({industry_df.loc[industry_df['涨跌幅'].idxmax(), '名称']})")
    print(f"  最低: {industry_df['涨跌幅'].min():.2f}% ({industry_df.loc[industry_df['涨跌幅'].idxmin(), '名称']})")
    
    print(f"\n市值:")
    print(f"  总市值: {industry_df['总市值'].sum():.2f} 亿元")
    print(f"  平均市值: {industry_df['总市值'].mean():.2f} 亿元")
    
    # 排名
    print("\n" + "=" * 80)
    print("【三、涨幅排行】")
    print("=" * 80)
    sorted_df = industry_df.sort_values('涨跌幅', ascending=False)
    print(sorted_df[['代码', '名称', '最新价', '涨跌幅']].to_string(index=False))
    
    print("\n" + "=" * 80)
    print("【四、市值排行】")
    print("=" * 80)
    sorted_by_cap = industry_df.sort_values('总市值', ascending=False)
    print(sorted_by_cap[['代码', '名称', '总市值', '涨跌幅']].to_string(index=False))
    
    print("\n" + "=" * 80)
    print("【五、新易盛在行业中的位置】")
    print("=" * 80)
    
    xys = industry_df[industry_df['代码'] == '300502']
    if not xys.empty:
        xys_data = xys.iloc[0]
        
        # 涨跌幅排名
        zhangfu_rank = (industry_df['涨跌幅'] > xys_data['涨跌幅']).sum() + 1
        # 市值排名
        shizhi_rank = (industry_df['总市值'] > xys_data['总市值']).sum() + 1
        
        print(f"\n新易盛数据:")
        print(f"  最新价: {xys_data['最新价']:.2f}元")
        print(f"  涨跌幅: {xys_data['涨跌幅']:.2f}% (排名: {zhangfu_rank}/{len(industry_df)})")
        print(f"  总市值: {xys_data['总市值']:.2f}亿元 (排名: {shizhi_rank}/{len(industry_df)})")
        print(f"  成交额: {xys_data['成交额']:.2f}")
        print(f"  换手率: {xys_data['换手率']:.2f}%")
        
else:
    print("\n未能获取任何数据")

print("\n" + "=" * 80)
