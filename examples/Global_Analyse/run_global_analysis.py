"""
全局板块加权分析 (基于 stock_list.xml)
"""
import sys
import os
from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET

import concurrent.futures
import matplotlib.pyplot as plt

# 添加项目根目录到路径
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.data_fetch.stock_data import StockDataFetcher
from examples.Global_Analyse.report_generator import generate_report

# 配置输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_stock_config(xml_path):
    """
    解析 stock_list.xml
    Returns:
        dict: {
            'blocks': {
                'BlockName': [{'name': stock_name, 'code': stock_code}, ...]
            },
            'all_stocks': [] # list of dict {'name': name, 'code': code}
        }
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    config = {
        'blocks': {},
        'all_stocks': []
    }
    
    for block in root.findall('Block'):
        block_name = block.get('name')
        
        if block_name not in config['blocks']:
            config['blocks'][block_name] = []
            
        for stock in block.findall('Stock'):
            stock_name = stock.text.strip()
            stock_code = stock.get('code') # 获取代码属性
            
            stock_info = {'name': stock_name, 'code': stock_code}
            
            config['blocks'][block_name].append(stock_info)
            config['all_stocks'].append(stock_info)
            
    return config

def get_name_code_map(fetcher: StockDataFetcher) -> dict:
    """
    获取 股票名称 -> 股票代码 的映射
    支持本地缓存以加快速度
    """
    cache_file = os.path.join(project_root, "data", "stock_list_cache.csv")
    df = None
    
    # 1. 尝试读取缓存
    if os.path.exists(cache_file):
        try:
            # 检查缓存文件的修改时间，如果太旧(例如超过24小时)则重新获取
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 86400: # 24小时
                print(f"读取本地股票列表缓存: {cache_file}")
                df = pd.read_csv(cache_file, dtype={'代码': str})
            else:
                print("本地缓存已过期，准备重新获取...")
        except Exception as e:
            print(f"读取缓存失败: {e}")
            
    # 2. 如果没有缓存或读取失败，则在线获取
    if df is None or df.empty:
        print("正在获取全市场股票列表以匹配代码 (首次运行可能需要1-2分钟，请耐心等待)...")
        df = fetcher.get_stock_list()
        
        if df is not None and not df.empty:
            # 保存缓存
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                df.to_csv(cache_file, index=False, encoding='utf-8-sig')
                print(f"股票列表已缓存至: {cache_file}")
            except Exception as e:
                print(f"保存缓存失败: {e}")
    
    if df is None or df.empty:
        print("❌ 无法获取全市场股票列表")
        return {}
    
    # 建立映射: 名称 -> 代码
    # 注意：可能有重名，这里简单处理，取第一个匹配的
    name_code_map = df.set_index('名称')['代码'].to_dict()
    return name_code_map

def calculate_historical_metrics(df: pd.DataFrame) -> dict:
    """
    计算基于历史数据的指标 (如5日均量)
    """
    # 确保按日期排序
    df = df.sort_values('日期').reset_index(drop=True)
    
    # 确保数值类型
    df['成交量'] = pd.to_numeric(df['成交量'], errors='coerce')
    df['收盘'] = pd.to_numeric(df['收盘'], errors='coerce')
    df['开盘'] = pd.to_numeric(df['开盘'], errors='coerce')
    
    # 计算涨跌幅 (如果历史数据里没有)
    df['PctChange'] = df['收盘'].pct_change() * 100
    
    # 取最近5天
    if len(df) < 5:
        return None
        
    last_5 = df.iloc[-5:]
    
    vol_ma5 = last_5['成交量'].mean()
    pct_ma5 = last_5['PctChange'].mean()
    
    # 红盘天数
    is_red = (last_5['收盘'] > last_5['开盘']).astype(int)
    red_days = is_red.sum()
    
    return {
        'VolMA5': vol_ma5,
        'PctChangeMA5': pct_ma5,
        'RedDays': red_days
    }

def fetch_stock_history(code, fetcher):
    """获取单个股票历史数据 (用于多线程)"""
    try:
        # 获取最近一年的数据用于计算均线等
        return fetcher.get_stock_hist(code, start_date="20240101", end_date="20251231")
    except Exception as e:
        print(f"获取 {code} 历史数据失败: {e}")
        return None

def main():
    print("=" * 50)
    print("开始全局板块加权分析")
    print("=" * 50)
    
    xml_path = os.path.join(project_root, "data", "stock_list.xml")
    if not os.path.exists(xml_path):
        print(f"❌ 找不到配置文件: {xml_path}")
        return
        
    # 1. 加载配置
    print(f"读取配置文件: {xml_path}")
    config = load_stock_config(xml_path)
    all_stocks = config['all_stocks']
    print(f"共找到 {len(all_stocks)} 个待分析股票")
    
    fetcher = StockDataFetcher()
    
    # 2. 准备代码列表
    valid_stocks = {} # name -> code
    missing_stocks = []
    
    # 优先使用 XML 中的 code
    stocks_without_code = []
    for s in all_stocks:
        if s.get('code'):
            valid_stocks[s['name']] = s['code']
        else:
            stocks_without_code.append(s['name'])
            
    # 如果有股票没有代码，尝试在线获取
    if stocks_without_code:
        print(f"⚠️ 有 {len(stocks_without_code)} 个股票在XML中未配置代码，尝试在线匹配...")
        name_code_map = get_name_code_map(fetcher)
        
        for name in stocks_without_code:
            if name in name_code_map:
                code = name_code_map[name]
                # 确保带前缀
                code = fetcher._add_market_prefix(code)
                valid_stocks[name] = code
                print(f"  ✅ 匹配成功: {name} -> {code}")
            else:
                missing_stocks.append(name)
    
    if missing_stocks:
        print(f"⚠️ 以下股票未找到代码 (可能名称不匹配): {', '.join(missing_stocks)}")
        
    if not valid_stocks:
        print("❌ 没有找到任何有效股票代码")
        return

    # 3. 批量获取实时行情
    print(f"正在获取 {len(valid_stocks)} 只股票的实时行情 (腾讯源)...")
    all_codes = list(valid_stocks.values())
    realtime_df = fetcher.get_stock_realtime_batch(all_codes)
    
    if realtime_df.empty:
        print("❌ 无法获取实时行情")
        return
        
    # 确保代码列是字符串类型，防止匹配失败
    realtime_df['代码'] = realtime_df['代码'].astype(str)
    
    # 统一处理：去掉前缀进行匹配
    realtime_df['简码'] = realtime_df['代码'].apply(lambda x: x[2:] if x.startswith(('sh', 'sz', 'bj')) else x)
    
    # 重新建立映射，使用简码作为key
    realtime_map = realtime_df.set_index('简码').to_dict('index')
    
    # 4. 多线程获取历史数据
    print(f"\n正在多线程获取 {len(valid_stocks)} 只股票的历史数据 (16线程)...")
    history_data_map = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_code = {
            executor.submit(fetch_stock_history, code, fetcher): code 
            for code in valid_stocks.values()
        }
        
        completed = 0
        total = len(future_to_code)
        
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            completed += 1
            print(f"[{completed}/{total}] 获取历史数据...", end="\r")
            
            try:
                df = future.result()
                if df is not None and not df.empty:
                    history_data_map[code] = df
            except Exception as e:
                print(f"\n{code} 获取失败: {e}")
                
    print(f"\n成功获取 {len(history_data_map)} 只股票的历史数据")
    
    # 5. 遍历并计算指标 (单线程分析)
    print("\n开始计算个股指标...")
    results = []
    total_stocks = len(valid_stocks)
    processed = 0
    
    for block, stock_list in config['blocks'].items():
        for stock_info in stock_list:
            name = stock_info['name']
            if name not in valid_stocks:
                continue
                
            full_code = valid_stocks[name]
            # 获取简码用于查找
            simple_code = full_code[2:] if full_code.startswith(('sh', 'sz', 'bj')) else full_code
            
            processed += 1
            # 简单的进度显示
            if processed % 10 == 0:
                print(f"[{processed}/{total_stocks}] 分析中...", end="\r")
            
            if simple_code not in realtime_map:
                # 尝试直接用 full_code 查找
                if full_code not in realtime_map:
                    continue
                else:
                    simple_code = full_code
                
            rt_data = realtime_map[simple_code]
            
            try:
                # 从预获取的字典中拿历史数据
                df = history_data_map.get(full_code)
                
                if df is not None and not df.empty:
                    hist_metrics = calculate_historical_metrics(df)
                    
                    if hist_metrics:
                        current_vol = rt_data['成交量']
                        current_pct = rt_data['涨跌幅']
                        vol_ma5 = hist_metrics['VolMA5']
                        
                        vol_dev = (current_vol - vol_ma5) / vol_ma5 if vol_ma5 > 0 else 0
                        pct_dev = current_pct - hist_metrics['PctChangeMA5']
                        price_eff = abs(current_pct) / (vol_ma5 / 10000) if vol_ma5 > 0 else 0
                        
                        results.append({
                            'Block': block,
                            '代码': full_code,
                            '名称': name,
                            '日期': datetime.now().strftime("%Y-%m-%d"),
                            '收盘': rt_data['最新价'],
                            '成交量': current_vol,
                            '成交额': rt_data['成交额'],
                            '涨跌幅(%)': round(current_pct, 2),
                            '量比偏差': round(vol_dev, 4),
                            '涨跌幅偏差': round(pct_dev, 2),
                            '红盘天数': int(hist_metrics['RedDays']),
                            '量价效率': round(price_eff, 4),
                            '总市值': rt_data['总市值']
                        })
            except Exception as e:
                print(f"分析 {name} 失败: {e}")

    print(f"\n处理完成，共生成 {len(results)} 条分析结果")

    if not results:
        print("未获取到有效数据")
        return

    df_results = pd.DataFrame(results)
    
    # ==========================================
    # 聚合分析
    # ==========================================
    
    # 1. Block 级别聚合
    block_stats = []
    for blk, group_df in df_results.groupby('Block'):
        group_df['成交额'] = pd.to_numeric(group_df['成交额'], errors='coerce').fillna(0)
        total_amount = group_df['成交额'].sum()
        
        if total_amount > 0:
            # 使用成交额加权
            weighted_pct = (group_df['涨跌幅(%)'] * group_df['成交额']).sum() / total_amount
        else:
            weighted_pct = group_df['涨跌幅(%)'].mean()
            
        block_stats.append({
            '细分板块': blk,
            '成交额加权涨跌幅(%)': round(weighted_pct, 2),
            '包含个股数': len(group_df),
            '总成交额(亿)': round(total_amount / 100000000, 2)
        })
        
    df_block = pd.DataFrame(block_stats).sort_values('成交额加权涨跌幅(%)', ascending=False)
    
    # ==========================================
    # 输出结果
    # ==========================================
    print("\\n" + "="*60)
    print("【表1】细分板块 (Block) 成交额加权涨跌幅排名")
    print("="*60)
    print(df_block.to_string(index=False))
    
    # 打印每个细分板块的个股详情
    print("\\n" + "="*60)
    print("【表2】细分板块个股详情")
    print("="*60)
    
    # 对 df_results 进行排序：优先按板块在 df_block 中的顺序 (即涨跌幅排名)，其次按个股成交额
    # 1. 创建板块排名映射
    block_rank_map = {row['细分板块']: i for i, row in df_block.reset_index().iterrows()}
    
    # 2. 添加临时排名列
    df_results['__block_rank'] = df_results['Block'].map(block_rank_map)
    
    # 3. 排序
    df_results = df_results.sort_values(['__block_rank', '成交额'], ascending=[True, False])
    
    # 4. 删除临时列
    df_results = df_results.drop(columns=['__block_rank'])
    
    # 按排序后的顺序打印
    current_block = None
    for _, row in df_results.iterrows():
        if row['Block'] != current_block:
            current_block = row['Block']
            print(f"\\n>>> {current_block}")
            
        amt_yi = row['成交额'] / 100000000
        mkt_yi = row['总市值'] / 100000000
        print(f"  {row['名称']:8s} ({row['代码']}): 成交额 {amt_yi:>6.2f} 亿  市值 {mkt_yi:>7.2f} 亿  涨跌幅: {row['涨跌幅(%)']:>6.2f}%")

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存明细 (此时 df_results 已经是排序好的)
    detail_file = os.path.join(OUTPUT_DIR, f"global_analysis_details_{timestamp}.csv")
    df_results.to_csv(detail_file, index=False, encoding='utf-8-sig')
    
    # 保存板块统计
    block_file = os.path.join(OUTPUT_DIR, "global_analysis_blocks.csv")
    df_block.to_csv(block_file, index=False, encoding='utf-8-sig')
    
    print(f"\\n✅ 结果已保存至目录: {OUTPUT_DIR}")
    
    # 生成可视化报告
    generate_report(df_block, df_results, OUTPUT_DIR, timestamp)

if __name__ == "__main__":
    main()
