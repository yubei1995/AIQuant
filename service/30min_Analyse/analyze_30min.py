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
from generate_30min_report import generate_30min_report

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

def get_name_code_map(fetcher: StockDataFetcher) -> dict:
    # Reuse the logic from block_analysis_service or just rely on XML codes
    # For simplicity, let's assume XML has codes or we fetch them if missing
    # But here we will try to use what we have.
    return {} 

def fetch_30min_data(code):
    """
    Fetch 30-minute data using Tencent Minute API.
    Aggregates 1-minute data to 30-minute bars.
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
            
        min_data = stock_data['data']['data']
        if not min_data:
            return None
            
        # Parse data
        # Format: "0930 14.50 100 145000.00" (Time, Price, Volume, Amount)
        records = []
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for item in min_data:
            parts = item.split(' ')
            if len(parts) < 2: continue
            
            time_str = parts[0] # HHMM
            price = float(parts[1])
            
            # Amount might be missing or at index 3
            amount = 0.0
            if len(parts) >= 4:
                amount = float(parts[3])
            
            # Determine 30min bar
            hm = int(time_str)
            bar_time = None
            
            if hm <= 1000: bar_time = "10:00:00"
            elif hm <= 1030: bar_time = "10:30:00"
            elif hm <= 1100: bar_time = "11:00:00"
            elif hm <= 1130: bar_time = "11:30:00"
            elif hm < 1300: continue # Lunch break noise
            elif hm <= 1330: bar_time = "13:30:00"
            elif hm <= 1400: bar_time = "14:00:00"
            elif hm <= 1430: bar_time = "14:30:00"
            elif hm <= 1500: bar_time = "15:00:00"
            else: continue # After market
            
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
        # Amount: sum of amounts
        df_agg = df.groupby('bar_time').agg({
            'price': 'last',
            'amount': 'sum'
        }).reset_index()
        
        df_agg['时间'] = today_str + ' ' + df_agg['bar_time']
        df_agg.rename(columns={'price': '收盘', 'amount': '成交额'}, inplace=True)
        
        # Sort by time
        df_agg.sort_values('时间', inplace=True)
        
        return df_agg[['时间', '收盘', '成交额']]

    except Exception as e:
        # print(f"Tencent fetch failed for {code}: {e}")
        return None

def process_block_data(block_name, stock_list, valid_stocks):
    """
    Calculate aggregated 30min data for a block.
    """
    block_data = {} # time -> {'close_sum': 0, 'vol_sum': 0, 'count': 0}
    
    # We need to align timestamps.
    # Let's fetch one stock first to get the standard timestamps? 
    # Or just collect all and merge.
    
    dfs = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_stock = {}
        for stock_info in stock_list:
            name = stock_info['name']
            if name in valid_stocks:
                code = valid_stocks[name]
                future_to_stock[executor.submit(fetch_30min_data, code)] = name
        
        for future in concurrent.futures.as_completed(future_to_stock):
            res = future.result()
            if res is not None:
                dfs.append(res)
                
    if not dfs:
        return None
        
    # Merge all dataframes
    # We want to calculate an "Index". 
    # Simple approach: Sum of Market Caps? We don't have realtime market cap in 30min data easily.
    # Alternative: Average Cumulative Return.
    # For each stock, calculate pct change relative to the first bar of the day.
    # Then average these pct changes for the block.
    
    # 1. Normalize each stock
    normalized_series = []
    volume_series = []
    
    common_time_index = None
    
    for df in dfs:
        df = df.sort_values('时间').reset_index(drop=True)
        if df.empty: continue
        
        # Use the first timestamp as baseline?
        # Or just use the first row's open? We only have Close here.
        # Let's use the first row's Close as base (0%).
        base_price = df.iloc[0]['收盘']
        if base_price == 0: continue
        
        # Calculate pct change series
        pct_series = (df['收盘'] - base_price) / base_price * 100
        pct_series.index = df['时间']
        normalized_series.append(pct_series)
        
        # Volume
        vol = df['成交额']
        vol.index = df['时间']
        volume_series.append(vol)
        
    if not normalized_series:
        return None
        
    # Concatenate and mean
    # This handles missing timestamps by aligning to union of indices
    all_pct = pd.concat(normalized_series, axis=1)
    avg_pct = all_pct.mean(axis=1).sort_index()
    
    all_vol = pd.concat(volume_series, axis=1)
    total_vol = all_vol.sum(axis=1).sort_index()
    
    # Format for JSON
    # Times should be strings
    times = avg_pct.index.tolist()
    values = avg_pct.values.tolist()
    volumes = total_vol.values.tolist()
    
    return {
        'name': block_name,
        'times': times,
        'values': [round(v, 2) for v in values],
        'volumes': [round(v, 2) for v in volumes]
    }

def main():
    print("Starting 30-Min Analysis...")
    
    xml_path = os.path.join(project_root, "data", "stock_list.xml")
    if not os.path.exists(xml_path):
        print(f"Config not found: {xml_path}")
        return
        
    config = load_stock_config(xml_path)
    
    # Resolve codes
    fetcher = StockDataFetcher()
    valid_stocks = {}
    all_stocks = config['all_stocks']
    
    # Simple resolution
    for s in all_stocks:
        if s.get('code'):
            valid_stocks[s['name']] = s['code']
            
    # Process Blocks
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
        
    # Save Data to JSON
    date_str = datetime.now().strftime("%Y%m%d")
    json_path = os.path.join(OUTPUT_DIR, f"30min_data_{date_str}.json")
    
    # Convert list to map for easier JSON structure
    data_map = {}
    for item in block_results:
        data_map[item['name']] = {
            'times': item['times'],
            'values': item['values'],
            'volumes': item['volumes']
        }
        
    print(f"Saving data to {json_path}...")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data_map, f, ensure_ascii=False, indent=4)
        
    # Generate HTML
    html_path = os.path.join(OUTPUT_DIR, f"30min_analysis_{date_str}.html")
    print("Generating HTML report...")
    generate_30min_report(json_path, html_path)
    
    if os.name == 'nt':
        os.startfile(html_path)

if __name__ == "__main__":
    main()
