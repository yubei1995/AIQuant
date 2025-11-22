"""
通信设备行业分析
"""
import akshare as ak
import pandas as pd
import time

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_rows', 50)

print("=" * 80)
print("通信设备行业分析报告")
print("=" * 80)

# 1. 获取行业列表
print("\n【一、行业列表】")
try:
    industry_list = ak.stock_board_industry_name_em()
    print(f"共有 {len(industry_list)} 个行业板块")
    
    # 查找通信相关行业
    comm_industries = industry_list[industry_list['板块名称'].str.contains('通信', na=False)]
    print("\n通信相关行业:")
    print(comm_industries[['板块名称', '板块代码', '最新价', '涨跌幅', '总市值', '换手率']].to_string(index=False))
except Exception as e:
    print(f"获取行业列表失败: {e}")
    print("继续尝试获取通信设备行业成份股...")

# 2. 获取通信设备行业成份股
print("\n" + "=" * 80)
print("【二、通信设备行业成份股】")
print("=" * 80)

try:
    # 添加延迟避免请求过快
    time.sleep(2)
    
    industry_stocks = ak.stock_board_industry_cons_em(symbol="通信设备")
    
    print(f"\n通信设备行业共有 {len(industry_stocks)} 只股票\n")
    
    # 显示所有成份股
    print("【行业所有成份股】")
    display_cols = ['序号', '代码', '名称', '最新价', '涨跌幅', '涨跌额', '成交量', 
                    '成交额', '振幅', '换手率', '市盈率-动态', '市净率']
    available_cols = [col for col in display_cols if col in industry_stocks.columns]
    print(industry_stocks[available_cols].to_string(index=False))
    
    # 3. 行业统计
    print("\n" + "=" * 80)
    print("【三、行业统计分析】")
    print("=" * 80)
    
    print(f"\n涨跌分布:")
    up_count = len(industry_stocks[industry_stocks['涨跌幅'] > 0])
    down_count = len(industry_stocks[industry_stocks['涨跌幅'] < 0])
    flat_count = len(industry_stocks[industry_stocks['涨跌幅'] == 0])
    print(f"  上涨: {up_count} 只 ({up_count/len(industry_stocks)*100:.1f}%)")
    print(f"  下跌: {down_count} 只 ({down_count/len(industry_stocks)*100:.1f}%)")
    print(f"  平盘: {flat_count} 只 ({flat_count/len(industry_stocks)*100:.1f}%)")
    
    print(f"\n涨跌幅统计:")
    print(f"  平均涨跌幅: {industry_stocks['涨跌幅'].mean():.2f}%")
    print(f"  最大涨幅: {industry_stocks['涨跌幅'].max():.2f}%")
    print(f"  最大跌幅: {industry_stocks['涨跌幅'].min():.2f}%")
    
    if '换手率' in industry_stocks.columns:
        print(f"\n换手率统计:")
        print(f"  平均换手率: {industry_stocks['换手率'].mean():.2f}%")
        print(f"  最高换手率: {industry_stocks['换手率'].max():.2f}%")
    
    # 4. 涨幅榜
    print("\n" + "=" * 80)
    print("【四、涨幅榜 TOP 10】")
    print("=" * 80)
    top10 = industry_stocks.nlargest(10, '涨跌幅')
    print(top10[['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率', '市盈率-动态']].to_string(index=False))
    
    # 5. 跌幅榜
    print("\n" + "=" * 80)
    print("【五、跌幅榜 TOP 10】")
    print("=" * 80)
    bottom10 = industry_stocks.nsmallest(10, '涨跌幅')
    print(bottom10[['代码', '名称', '最新价', '涨跌幅', '成交量', '换手率', '市盈率-动态']].to_string(index=False))
    
    # 6. 成交活跃榜
    print("\n" + "=" * 80)
    print("【六、成交活跃榜 TOP 10】")
    print("=" * 80)
    active10 = industry_stocks.nlargest(10, '成交额')
    print(active10[['代码', '名称', '最新价', '涨跌幅', '成交额', '换手率']].to_string(index=False))
    
    # 7. 市值排行
    if '总市值' in industry_stocks.columns:
        print("\n" + "=" * 80)
        print("【七、市值排行 TOP 10】")
        print("=" * 80)
        market_cap10 = industry_stocks.nlargest(10, '总市值')
        print(market_cap10[['代码', '名称', '最新价', '涨跌幅', '总市值', '市盈率-动态']].to_string(index=False))
    
    # 8. 新易盛在行业中的位置
    print("\n" + "=" * 80)
    print("【八、新易盛(300502)在行业中的位置】")
    print("=" * 80)
    
    xingyisheng = industry_stocks[industry_stocks['代码'] == '300502']
    if not xingyisheng.empty:
        row = xingyisheng.iloc[0]
        
        # 涨跌幅排名
        zhangdiefu_rank = (industry_stocks['涨跌幅'] > row['涨跌幅']).sum() + 1
        print(f"\n涨跌幅: {row['涨跌幅']:.2f}%")
        print(f"  排名: {zhangdiefu_rank}/{len(industry_stocks)}")
        
        # 成交额排名
        chengjiao_rank = (industry_stocks['成交额'] > row['成交额']).sum() + 1
        print(f"\n成交额: {row['成交额']:.2f}")
        print(f"  排名: {chengjiao_rank}/{len(industry_stocks)}")
        
        # 市值排名
        if '总市值' in industry_stocks.columns and pd.notna(row['总市值']):
            shizhirank = (industry_stocks['总市值'] > row['总市值']).sum() + 1
            print(f"\n总市值: {row['总市值']:.2f}")
            print(f"  排名: {shizhirank}/{len(industry_stocks)}")
        
        print(f"\n新易盛详细数据:")
        print(xingyisheng[['代码', '名称', '最新价', '涨跌幅', '换手率', '市盈率-动态', '市净率']].to_string(index=False))
    else:
        print("未找到新易盛(300502)的数据")
        
except Exception as e:
    print(f"获取通信设备行业数据失败: {e}")
    print("\n可能的原因:")
    print("1. 网络连接问题")
    print("2. API访问限制")
    print("3. 请稍后重试")

print("\n" + "=" * 80)
print("报告生成完毕")
print("=" * 80)
