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
            
        # Try to get previous close from 'qt'
        prev_close = None
        if 'qt' in stock_data and tencent_code in stock_data['qt']:
            qt_data = stock_data['qt'][tencent_code]
            # qt_data is usually a list. Index 4 is PrevClose.
            if isinstance(qt_data, list) and len(qt_data) > 4:
                try:
                    prev_close = float(qt_data[4])
                except:
                    pass

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
        # Amount: sum of amounts? 
        # Wait, Tencent minute data 'amount' is usually cumulative turnover for the day?
        # Let's check the raw data format.
        # Usually minute data returns cumulative volume/amount.
        # If so, we need to calculate diff.
        # But wait, if it's minute data, usually it's per minute.
        # However, if the chart shows increasing bars, it means we are summing up cumulative values or the source is cumulative.
        
        # Let's assume Tencent returns cumulative amount.
        # If so, we need to take the last amount of the bucket - last amount of previous bucket.
        # But here we are grouping by bar_time and summing 'amount'.
        # If 'amount' in raw data is cumulative, summing it is wrong.
        # If 'amount' is per minute, summing it is correct for the interval.
        
        # Let's look at the values in JSON.
        # "volumes": [175亿, 454亿, 574亿...] -> Clearly increasing.
        # This suggests that the 'amount' we get from Tencent is CUMULATIVE for the day.
        
        # If Tencent returns cumulative amount:
        # We should take the MAX amount in the bucket as the cumulative amount at that time.
        # Then calculate the difference between buckets to get interval amount.
        
        df_agg = df.groupby('bar_time').agg({
            'price': 'last',
            'amount': 'max' # Take max (cumulative) amount in the bucket
        }).reset_index()
        
        df_agg['时间'] = today_str + ' ' + df_agg['bar_time']
        df_agg.rename(columns={'price': '收盘', 'amount': '累积成交额'}, inplace=True)
        
        # Sort by time
        df_agg.sort_values('时间', inplace=True)
        
        # Calculate Interval Amount
        # Interval = Current Cumulative - Previous Cumulative
        # For the first bucket, it's just the value (minus 0 or pre-market, but we assume 0)
        df_agg['成交额'] = df_agg['累积成交额'].diff().fillna(df_agg['累积成交额'])
        
        return df_agg[['时间', '收盘', '成交额']], prev_close

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
    interval_pct_series_list = [] # New list for interval pcts
    volume_series = []
    
    common_time_index = None
    
    for item in dfs:
        df, prev_close = item
        df = df.sort_values('时间').reset_index(drop=True)
        if df.empty: continue
        
        # Use prev_close as baseline if available to match Block_Analyse (1d%)
        # Otherwise use the first row's Close
        base_price = prev_close if (prev_close and prev_close > 0) else df.iloc[0]['收盘']
        if base_price == 0: continue
        
        # Calculate pct change series (Cumulative from Pre-Close)
        pct_series = (df['收盘'] - base_price) / base_price * 100
        pct_series.index = df['时间']
        normalized_series.append(pct_series)
        
        # Calculate Interval Pct Change (Current Close vs Previous Bar Close)
        # For the first bar, compare with Pre-Close
        # We can use pct_change() on the Close series, but need to handle the first element carefully
        # Or just calculate manually
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
        # We need to store this separately. Let's use a separate list.
        # But process_block_data structure is getting complex.
        # Let's attach it to the dataframe or create a new list.
        # To minimize changes, let's create a new list 'interval_pct_series_list'
        # But we need to pass it down.
        # Let's just add it to normalized_series as a tuple? No, that breaks concat.
        
        # Let's create a parallel list for interval pcts
        if 'interval_pct_series_list' not in locals():
            interval_pct_series_list = []
        interval_pct_series_list.append(interval_pct_series)
        
        # Volume
        vol = df['成交额']
        vol.index = df['时间']
        volume_series.append(vol)
        
    if not normalized_series:
        return None
        
    # Concatenate and mean
    # This handles missing timestamps by aligning to union of indices
    # Use ignore_index=True to avoid duplicate column names (all series named '收盘' or '成交额')
    all_pct = pd.concat(normalized_series, axis=1, ignore_index=True)
    all_interval_pct = pd.concat(interval_pct_series_list, axis=1, ignore_index=True) # New: Interval Pcts
    all_vol = pd.concat(volume_series, axis=1, ignore_index=True)
    
    # --- Top Chart: Cumulative Turnover Weighted Index ---
    # Weight at time t = Cumulative Turnover from start to t
    cumulative_vol = all_vol.cumsum()
    
    # Numerator: Sum(Pct * Cumulative_Weight)
    cumulative_weighted_sum = (all_pct * cumulative_vol).sum(axis=1)
    
    # Denominator: Sum(Cumulative_Weight) where Pct is not NaN
    valid_mask = all_pct.notna().astype(int)
    cumulative_weights_sum = (cumulative_vol * valid_mask).sum(axis=1)
    
    # Calculate average
    avg_pct = cumulative_weighted_sum.divide(cumulative_weights_sum).fillna(0).sort_index()
    
    # --- Bottom Chart: Interval Turnover Weighted Index ---
    # Weight at time t = Turnover in the specific 30min interval (all_vol)
    # Value to weight = Interval Pct Change (all_interval_pct)
    
    # Numerator: Sum(Interval_Pct * Interval_Weight)
    dynamic_weighted_sum = (all_interval_pct * all_vol).sum(axis=1)
    
    # Denominator: Sum(Interval_Weight) where Interval_Pct is not NaN
    valid_mask_interval = all_interval_pct.notna().astype(int)
    dynamic_weights_sum = (all_vol * valid_mask_interval).sum(axis=1)
    
    dynamic_avg_pct = dynamic_weighted_sum.divide(dynamic_weights_sum).fillna(0).sort_index()
    
    # Interval Volume (for Bottom Chart)
    total_vol = all_vol.sum(axis=1).sort_index()
    
    # Cumulative Volume (for Top Chart)
    cumulative_total_vol = total_vol.cumsum()
    
    # Format for JSON
    # Times should be strings
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
            'dynamic_values': item.get('dynamic_values', []), # Ensure field exists
            'volumes': item['volumes'],
            'cum_volumes': item.get('cum_volumes', []) # Ensure field exists
        }
        
    print(f"Saving data to {json_path}...")
    # Debug print to check if fields are populated
    if block_results:
        first_res = block_results[0]
        print(f"Debug: First block '{first_res['name']}' has keys: {list(first_res.keys())}")
        
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
