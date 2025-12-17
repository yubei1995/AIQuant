import sys
import os
from pathlib import Path
import time
from datetime import datetime
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import concurrent.futures
import akshare as ak
import json
import requests

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from src.data_fetch.stock_data import StockDataFetcher
from generate_5min_report import generate_5min_report

# Configure Output Directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_stock_config(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    config = {'blocks': {}, 'all_stocks': []}
    for block in root.findall('Block'):
        block_name = block.get('name')
        if block_name not in config['blocks']:
            config['blocks'][block_name] = []
        for stock in block.findall('Stock'):
            stock_name = stock.text.strip()
            stock_code = stock.get('code')
            stock_info = {'name': stock_name, 'code': stock_code}
            config['blocks'][block_name].append(stock_info)
            config['all_stocks'].append(stock_info)
    return config

def get_5min_bar_time(hm_int):
    """
    Convert HHMM integer to HH:MM:00 string, rounded up to nearest 5 minutes.
    """
    # Handle start times mapping to first bar
    if hm_int == 930: return "09:35:00"
    if hm_int == 1300: return "13:05:00"
    
    hour = hm_int // 100
    minute = hm_int % 100
    
    # Round up to nearest 5
    remainder = minute % 5
    if remainder != 0:
        minute = minute + (5 - remainder)
    
    # Handle overflow
    if minute == 60:
        minute = 0
        hour += 1
        
    return f"{hour:02d}:{minute:02d}:00"

def fetch_5min_data(code):
    """
    Fetch 5-minute data using Tencent Minute API.
    Aggregates 1-minute data to 5-minute bars.
    """
    try:
        # Tencent code format
        tencent_code = code
        if not code.startswith(('sh', 'sz', 'bj')):
            if code.startswith('6'): tencent_code = f"sh{code}"
            elif code.startswith(('0', '3')): tencent_code = f"sz{code}"
            elif code.startswith(('4', '8')): tencent_code = f"bj{code}"
            
        url = f"http://web.ifzq.gtimg.cn/appstock/app/minute/query?code={tencent_code}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        if 'data' not in data or tencent_code not in data['data']:
            return None
            
        stock_data = data['data'][tencent_code]
        if 'data' not in stock_data or 'data' not in stock_data['data']:
            return None
            
        # Try to get previous close from 'qt'
        prev_close = None
        if 'qt' in stock_data and tencent_code in stock_data['qt']:
            qt_data = stock_data['qt'][tencent_code]
            if isinstance(qt_data, list) and len(qt_data) > 4:
                try:
                    prev_close = float(qt_data[4])
                except:
                    pass

        min_data = stock_data['data']['data']
        if not min_data:
            return None
            
        # Parse data
        records = []
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for item in min_data:
            parts = item.split(' ')
            if len(parts) < 2: continue
            
            time_str = parts[0] # HHMM
            price = float(parts[1])
            
            amount = 0.0
            if len(parts) >= 4:
                amount = float(parts[3])
            
            # Determine 5min bar
            hm = int(time_str)
            
            # Filter out non-trading hours
            if hm < 930 or (hm > 1130 and hm < 1300) or hm > 1500:
                continue
                
            bar_time = get_5min_bar_time(hm)
            
            records.append({
                'bar_time': bar_time,
                'price': price,
                'amount': amount
            })
            
        if not records:
            return None
            
        df = pd.DataFrame(records)
        
        # Aggregate
        # Close: last price in the bucket
        # Amount: max amount in the bucket (since it's cumulative)
        
        df_agg = df.groupby('bar_time').agg({
            'price': 'last',
            'amount': 'max' 
        }).reset_index()
        
        df_agg['时间'] = today_str + ' ' + df_agg['bar_time']
        df_agg.rename(columns={'price': '收盘', 'amount': '累积成交额'}, inplace=True)
        
        # Sort by time
        df_agg.sort_values('时间', inplace=True)
        
        # Calculate Interval Amount
        df_agg['成交额'] = df_agg['累积成交额'].diff().fillna(df_agg['累积成交额'])
        
        return df_agg[['时间', '收盘', '成交额']], prev_close

    except Exception as e:
        return None

def process_block_data(block_name, stock_list, valid_stocks):
    """
    Calculate aggregated 5min data for a block.
    """
    dfs = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_stock = {}
        for stock_info in stock_list:
            name = stock_info['name']
            if name in valid_stocks:
                code = valid_stocks[name]
                future_to_stock[executor.submit(fetch_5min_data, code)] = name
        
        for future in concurrent.futures.as_completed(future_to_stock):
            res = future.result()
            if res is not None:
                dfs.append(res)
                
    if not dfs:
        return None
        
    normalized_series = []
    interval_pct_series_list = []
    volume_series = []
    
    for item in dfs:
        df, prev_close = item
        df = df.sort_values('时间').reset_index(drop=True)
        if df.empty: continue
        
        base_price = prev_close if (prev_close and prev_close > 0) else df.iloc[0]['收盘']
        if base_price == 0: continue
        
        # Calculate pct change series (Cumulative from Pre-Close)
        pct_series = (df['收盘'] - base_price) / base_price * 100
        pct_series.index = df['时间']
        normalized_series.append(pct_series)
        
        # Calculate Interval Pct Change
        closes = df['收盘'].values
        interval_pcts = []
        for i in range(len(closes)):
            curr = closes[i]
            prev = base_price if i == 0 else closes[i-1]
            if prev > 0:
                p = (curr - prev) / prev * 100
            else:
                p = 0.0
            interval_pcts.append(p)
            
        interval_pct_series = pd.Series(interval_pcts, index=df['时间'])
        interval_pct_series_list.append(interval_pct_series)
        
        # Volume
        vol = df['成交额']
        vol.index = df['时间']
        volume_series.append(vol)
        
    if not normalized_series:
        return None
        
    all_pct = pd.concat(normalized_series, axis=1, ignore_index=True)
    all_interval_pct = pd.concat(interval_pct_series_list, axis=1, ignore_index=True)
    all_vol = pd.concat(volume_series, axis=1, ignore_index=True)
    
    # --- Top Chart: Cumulative Turnover Weighted Index ---
    cumulative_vol = all_vol.cumsum()
    cumulative_weighted_sum = (all_pct * cumulative_vol).sum(axis=1)
    valid_mask = all_pct.notna().astype(int)
    cumulative_weights_sum = (cumulative_vol * valid_mask).sum(axis=1)
    avg_pct = cumulative_weighted_sum.divide(cumulative_weights_sum).fillna(0).sort_index()
    
    # --- Bottom Chart: Interval Turnover Weighted Index ---
    dynamic_weighted_sum = (all_interval_pct * all_vol).sum(axis=1)
    valid_mask_interval = all_interval_pct.notna().astype(int)
    dynamic_weights_sum = (all_vol * valid_mask_interval).sum(axis=1)
    dynamic_avg_pct = dynamic_weighted_sum.divide(dynamic_weights_sum).fillna(0).sort_index()
    
    # Interval Volume
    total_vol = all_vol.sum(axis=1).sort_index()
    
    # Cumulative Volume
    cumulative_total_vol = total_vol.cumsum()
    
    times = avg_pct.index.tolist()
    values = avg_pct.values.tolist()
    dynamic_values = dynamic_avg_pct.values.tolist()
    volumes = total_vol.values.tolist()
    cum_volumes = cumulative_total_vol.values.tolist()
    
    return {
        'name': block_name,
        'times': times,
        'values': [round(v, 2) for v in values],
        'dynamic_values': [round(v, 2) for v in dynamic_values],
        'volumes': [round(v, 2) for v in volumes],
        'cum_volumes': [round(v, 2) for v in cum_volumes]
    }

def main():
    print("Starting 5-Min Analysis...")
    
    xml_path = os.path.join(project_root, "data", "stock_list.xml")
    if not os.path.exists(xml_path):
        print(f"Config not found: {xml_path}")
        return
        
    config = load_stock_config(xml_path)
    
    fetcher = StockDataFetcher()
    valid_stocks = {}
    all_stocks = config['all_stocks']
    
    for s in all_stocks:
        if s.get('code'):
            valid_stocks[s['name']] = s['code']
            
    block_results = []
    total_blocks = len(config['blocks'])
    processed = 0
    
    for block_name, stock_list in config['blocks'].items():
        processed += 1
        print(f"Processing block [{processed}/{total_blocks}]: {block_name}...")
        
        res = process_block_data(block_name, stock_list, valid_stocks)
        if res:
            block_results.append(res)
            
    if not block_results:
        print("No data generated.")
        return
        
    date_str = datetime.now().strftime("%Y%m%d")
    json_path = os.path.join(OUTPUT_DIR, f"5min_data_{date_str}.json")
    
    data_map = {}
    for item in block_results:
        data_map[item['name']] = {
            'times': item['times'],
            'values': item['values'],
            'dynamic_values': item.get('dynamic_values', []),
            'volumes': item['volumes'],
            'cum_volumes': item.get('cum_volumes', [])
        }
        
    print(f"Saving data to {json_path}...")
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data_map, f, ensure_ascii=False, indent=4)
        
    html_path = os.path.join(OUTPUT_DIR, f"5min_analysis_{date_str}.html")
    print("Generating HTML report...")
    generate_5min_report(json_path, html_path)
    
    if os.name == 'nt':
        os.startfile(html_path)

if __name__ == "__main__":
    main()
