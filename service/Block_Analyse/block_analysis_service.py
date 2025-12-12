"""
Advanced Global Block Analysis Service
- Multi-period cumulative returns (1d, 3d, 5d, 10d)
- Top 20 blocks split into 4 subplots
- Daily precise output naming
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
import traceback

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.data_fetch.stock_data import StockDataFetcher
from service.Block_Analyse.chart_generator import generate_advanced_charts
from service.Block_Analyse.generate_html_report import generate_html_report

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
    cache_file = os.path.join(project_root, "data", "stock_list_cache.csv")
    df = None
    if os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            if time.time() - mtime < 86400:
                df = pd.read_csv(cache_file, dtype={'代码': str})
        except Exception:
            pass
            
    if df is None or df.empty:
        print("Fetching stock list online...")
        df = fetcher.get_stock_list()
        if df is not None and not df.empty:
            try:
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                df.to_csv(cache_file, index=False, encoding='utf-8-sig')
            except Exception:
                pass
    
    if df is None or df.empty:
        return {}
    return df.set_index('名称')['代码'].to_dict()

def fetch_stock_history(code, fetcher):
    try:
        # Fetch enough history for 10-day calculation
        return fetcher.get_stock_hist(code, start_date="20240101", end_date="20251231")
    except Exception as e:
        print(f"Failed to fetch history for {code}: {e}")
        return None

def calculate_stock_period_returns(df: pd.DataFrame) -> dict:
    """
    Calculate cumulative returns for 1, 3, 5, 10 days.
    Returns: {'1d': float, '3d': float, '5d': float, '10d': float} (Percentages)
    """
    # Ensure sorted by date
    df = df.sort_values('日期').reset_index(drop=True)
    df['收盘'] = pd.to_numeric(df['收盘'], errors='coerce')
    
    if len(df) < 2:
        return None
        
    # Get the latest close price
    latest_close = df.iloc[-1]['收盘']
    if pd.isna(latest_close) or latest_close <= 0:
        return None
    
    periods = [1, 3, 5, 10]
    results = {}
    
    for p in periods:
        if len(df) > p:
            prev_close = df.iloc[-(p+1)]['收盘']
            if pd.notna(prev_close) and prev_close > 0:
                ret = (latest_close - prev_close) / prev_close * 100
                results[f'{p}d'] = ret
            else:
                results[f'{p}d'] = 0.0
        else:
            if len(df) > 1:
                first_close = df.iloc[0]['收盘']
                if pd.notna(first_close) and first_close > 0:
                    ret = (latest_close - first_close) / first_close * 100
                    results[f'{p}d'] = ret
                else:
                    results[f'{p}d'] = 0.0
            else:
                results[f'{p}d'] = 0.0
                
    return results

def calculate_historical_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate metrics based on historical data (e.g., 5-day MA volume)
    """
    # Ensure sorted by date
    df = df.sort_values('日期').reset_index(drop=True)
    
    # Ensure numeric types
    df['成交量'] = pd.to_numeric(df['成交量'], errors='coerce')
    df['收盘'] = pd.to_numeric(df['收盘'], errors='coerce')
    df['开盘'] = pd.to_numeric(df['开盘'], errors='coerce')
    
    # Calculate PctChange if not present
    df['PctChange'] = df['收盘'].pct_change() * 100
    
    # Take last 5 days
    if len(df) < 5:
        return None
        
    last_5 = df.iloc[-5:]
    
    vol_ma5 = last_5['成交量'].mean()
    pct_ma5 = last_5['PctChange'].mean()
    
    # Red days
    is_red = (last_5['收盘'] > last_5['开盘']).astype(int)
    red_days = is_red.sum()
    
    return {
        'VolMA5': vol_ma5,
        'PctChangeMA5': pct_ma5,
        'RedDays': red_days
    }

def main():
    print("Starting Advanced Block Analysis Service...")
    
    xml_path = os.path.join(project_root, "data", "stock_list.xml")
    if not os.path.exists(xml_path):
        print(f"Config not found: {xml_path}")
        return
        
    config = load_stock_config(xml_path)
    fetcher = StockDataFetcher()
    
    # Prepare stocks
    valid_stocks = {}
    all_stocks = config['all_stocks']
    
    # Simple mapping logic (assuming cache exists or online fetch works)
    name_code_map = get_name_code_map(fetcher)
    
    for s in all_stocks:
        if s.get('code'):
            valid_stocks[s['name']] = s['code']
        elif s['name'] in name_code_map:
            code = name_code_map[s['name']]
            code = fetcher._add_market_prefix(code)
            valid_stocks[s['name']] = code
            
    if not valid_stocks:
        print("No valid stocks found.")
        return

    # Fetch Realtime
    print(f"Fetching realtime data for {len(valid_stocks)} stocks...")
    realtime_df = fetcher.get_stock_realtime_batch(list(valid_stocks.values()))
    if realtime_df.empty:
        print("Failed to fetch realtime data.")
        return
        
    realtime_df['代码'] = realtime_df['代码'].astype(str)
    realtime_df['简码'] = realtime_df['代码'].apply(lambda x: x[2:] if x.startswith(('sh', 'sz', 'bj')) else x)
    realtime_map = realtime_df.set_index('简码').to_dict('index')
    
    # Fetch History (Multi-threaded)
    print("Fetching historical data (8 threads)...")
    history_data_map = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_code = {executor.submit(fetch_stock_history, code, fetcher): code for code in valid_stocks.values()}
        
        completed = 0
        total = len(future_to_code)
        
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            completed += 1
            if completed % 5 == 0:
                print(f"Progress: {completed}/{total}", end="\r")
            
            try:
                # 15s timeout per task to prevent hanging
                res = future.result(timeout=15)
                if res is not None and not res.empty:
                    history_data_map[code] = res
            except concurrent.futures.TimeoutError:
                print(f"\nTimeout fetching {code}")
            except Exception as e:
                print(f"\nError fetching {code}: {e}")
            
    print(f"\nFetched history for {len(history_data_map)} stocks.")
                
    # Analyze Blocks
    print("Analyzing blocks...")
    block_stats = []
    stock_details = []
    
    for block_name, stock_list in config['blocks'].items():
        block_returns = {'1d': [], '3d': [], '5d': [], '10d': []}
        weights = [] # Using turnover as weight
        
        for stock_info in stock_list:
            name = stock_info['name']
            if name not in valid_stocks: continue
            full_code = valid_stocks[name]
            simple_code = full_code[2:] if full_code.startswith(('sh', 'sz', 'bj')) else full_code
            
            # Get Realtime info for weight
            if simple_code not in realtime_map and full_code in realtime_map:
                simple_code = full_code # Fallback
                
            if simple_code in realtime_map:
                rt = realtime_map[simple_code]
                turnover = rt['成交额']
                
                # Get History Returns
                if full_code in history_data_map:
                    hist_df = history_data_map[full_code]
                    # Append today's data to history to calculate up-to-date cumulative returns?
                    # Actually, fetch_stock_history usually returns up to yesterday or today depending on time.
                    # If running during trading hours, history might not have today.
                    # We should use realtime price for 'today' and history for previous days.
                    
                    # Construct a temporary series including today
                    # But calculate_stock_period_returns expects a DataFrame.
                    # Let's append today's row to hist_df if date doesn't match.
                    
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # Ensure '日期' column is datetime
                    if not pd.api.types.is_datetime64_any_dtype(hist_df['日期']):
                        hist_df['日期'] = pd.to_datetime(hist_df['日期'])
                        
                    last_hist_date = hist_df.iloc[-1]['日期']
                    
                    # Create a copy to avoid modifying the cached df
                    calc_df = hist_df.copy()
                    
                    # Compare dates (convert last_hist_date to string YYYY-MM-DD for comparison)
                    last_date_str = last_hist_date.strftime("%Y-%m-%d")
                    
                    if last_date_str != today_str:
                        # Use derived close to ensure consistency with realtime pct change
                        # This avoids issues where realtime price is raw but history might be adjusted (or vice versa)
                        # or simply precision differences.
                        rt_pct = rt['涨跌幅']
                        last_close = hist_df.iloc[-1]['收盘']
                        derived_close = last_close * (1 + rt_pct / 100)
                        
                        new_row = pd.DataFrame([{
                            '日期': pd.to_datetime(today_str),
                            '收盘': derived_close,
                            '成交量': rt['成交量'],
                            '成交额': rt['成交额']
                        }])
                        calc_df = pd.concat([calc_df, new_row], ignore_index=True)
                    else:
                        # Update today's data in history if it exists
                        # Also use derived close for consistency if possible, but if it's already there, 
                        # we assume it's correct. However, to be safe, let's trust realtime pct more.
                        # But we can't easily know "yesterday" if today is already in df.
                        # Let's just update with realtime price.
                        calc_df.iloc[-1, calc_df.columns.get_loc('收盘')] = rt['最新价']
                    
                    returns = calculate_stock_period_returns(calc_df)
                    if returns:
                        # Force 1d return to match realtime exactly
                        returns['1d'] = rt['涨跌幅']
                        
                        # Add to block lists
                        # Weight by turnover (using today's turnover)
                        # If turnover is 0 or NaN, use small epsilon or skip
                        w = turnover if pd.notnull(turnover) and turnover > 0 else 0
                        if w > 0:
                            weights.append(w)
                            for p in ['1d', '3d', '5d', '10d']:
                                block_returns[p].append(returns[p])
                                
                    # Calculate Stock Details (from Global_Analyse)
                    hist_metrics = calculate_historical_metrics(hist_df) # Use original hist_df for MA calculation to avoid bias from today's partial data? 
                    # Actually Global_Analyse uses history up to yesterday for MA, and compares with today's realtime.
                    # Let's use hist_df (which might not have today yet, or we should ensure it doesn't).
                    # If hist_df has today, we should probably exclude it for MA calculation if we want "past 5 days".
                    # But calculate_historical_metrics takes last 5 rows.
                    
                    if hist_metrics:
                        current_vol = rt['成交量']
                        current_pct = rt['涨跌幅']
                        vol_ma5 = hist_metrics['VolMA5']
                        
                        vol_dev = (current_vol - vol_ma5) / vol_ma5 if vol_ma5 > 0 else 0
                        pct_dev = current_pct - hist_metrics['PctChangeMA5']
                        price_eff = abs(current_pct) / (vol_ma5 / 10000) if vol_ma5 > 0 else 0
                        
                        stock_details.append({
                            'Block': block_name,
                            '代码': full_code,
                            '名称': name,
                            '日期': today_str,
                            '收盘': rt['最新价'],
                            '成交量': current_vol,
                            '成交额': rt['成交额'],
                            '涨跌幅(%)': round(current_pct, 2),
                            '量比偏差': round(vol_dev, 4),
                            '涨跌幅偏差': round(pct_dev, 2),
                            '红盘天数': int(hist_metrics['RedDays']),
                            '量价效率': round(price_eff, 4),
                            '总市值': rt['总市值']
                        })
        
        # Calculate Block Weighted Average
        if weights:
            total_weight = sum(weights)
            block_res = {'细分板块': block_name}
            for p in ['1d', '3d', '5d', '10d']:
                # Weighted average
                weighted_sum = sum(r * w for r, w in zip(block_returns[p], weights))
                block_res[f'{p}(%)'] = round(weighted_sum / total_weight, 2)
            
            block_res['总成交额(亿)'] = round(total_weight / 100000000, 2)
            block_stats.append(block_res)
            
    if not block_stats:
        print("No block stats generated.")
        return
        
    df_block = pd.DataFrame(block_stats)
    # Sort by 1d(%) descending so the CSV matches the report ranking
    df_block = df_block.sort_values('1d(%)', ascending=False)
    
    # Output Block Stats
    date_str = datetime.now().strftime("%Y%m%d")
    block_csv_path = os.path.join(OUTPUT_DIR, f"block_statistics_{date_str}.csv")
    
    print(f"Saving block stats to {block_csv_path}...")
    df_block.to_csv(block_csv_path, index=False, encoding='utf-8-sig')
    
    # Output Stock Details
    if stock_details:
        df_details = pd.DataFrame(stock_details)
        
        # Sort details by Block rank (using the order from df_block)
        # Create a categorical type for 'Block' with the sorted order
        sorted_blocks = df_block['细分板块'].tolist()
        df_details['Block'] = pd.Categorical(df_details['Block'], categories=sorted_blocks, ordered=True)
        
        # Sort by Block (rank) then by PctChange (descending) within block
        df_details = df_details.sort_values(['Block', '涨跌幅(%)'], ascending=[True, False])
        
        details_csv_path = os.path.join(OUTPUT_DIR, f"global_analysis_details_{date_str}.csv")
        print(f"Saving stock details to {details_csv_path}...")
        df_details.to_csv(details_csv_path, index=False, encoding='utf-8-sig')
    
    # Generate Charts
    print("Generating charts...")
    chart_path = generate_advanced_charts(df_block, OUTPUT_DIR, date_str)
    print(f"Chart saved to {chart_path}")
    
    # Generate HTML Report
    print("Generating HTML report...")
    html_path = os.path.join(OUTPUT_DIR, f"global_analysis_report_{date_str}.html")
    generate_html_report(block_csv_path, html_path)
    
    # Open chart and report
    if os.name == 'nt':
        os.startfile(chart_path)
        os.startfile(html_path)

import traceback

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
