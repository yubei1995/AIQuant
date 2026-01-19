import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time

def fetch_margin_data(stock_list):
    """
    Fetch margin data for the latest available date.
    Returns a DataFrame with margin details for stocks in stock_list.
    """
    print("Fetching Margin Data...")
    # Margin data is usually T-1
    today = datetime.now()
    
    # Try last 5 days to find data
    df_sz = pd.DataFrame()
    df_sh = pd.DataFrame()
    last_date_str = ""
    
    for i in range(0, 5):
        date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
        try:
            # SZSE
            if df_sz.empty:
                print(f"Trying SZSE margin for {date_str}...")
                temp = ak.stock_margin_detail_szse(date=date_str)
                if temp is not None and not temp.empty:
                    df_sz = temp
                    df_sz['date'] = date_str
                    last_date_str = date_str # Record the date found
            
            # SSE
            if df_sh.empty:
                print(f"Trying SSE margin for {date_str}...")
                temp = ak.stock_margin_detail_sse(date=date_str)
                if temp is not None and not temp.empty:
                    df_sh = temp
                    df_sh['date'] = date_str
            
            if not df_sz.empty and not df_sh.empty:
                break
        except Exception as e:
            print(f"Margin fetch error for {date_str}: {e}")
            continue
    
    # Needs T-1 for SZSE Net Buy calculation if Repay not available
    df_sz_prev = pd.DataFrame()
    if not df_sz.empty:
        # Try to find previous trading day data for SZSE
        found_date = datetime.strptime(df_sz['date'].iloc[0], "%Y%m%d")
        for i in range(1, 10):
            prev_date_str = (found_date - timedelta(days=i)).strftime("%Y%m%d")
            try:
                print(f"Trying SZSE margin (prev) for {prev_date_str}...")
                temp = ak.stock_margin_detail_szse(date=prev_date_str)
                if temp is not None and not temp.empty:
                    df_sz_prev = temp
                    print(f"Found SZSE previous data for {prev_date_str}")
                    break
            except:
                pass

    # Combine
    results = []
    # Strip prefixes from target codes for comparison if margin data uses pure codes
    target_codes_pure = {s['code'][2:] if s['code'].startswith(('sh', 'sz', 'bj')) else s['code'] for s in stock_list}
    target_codes_full = {s['code'] for s in stock_list}
    
    # Process SZSE
    if not df_sz.empty:
        # Optimize prev lookup
        sz_prev_map = {}
        if not df_sz_prev.empty:
            # Create dict: code -> margin_balance
            for _, row in df_sz_prev.iterrows():
                code = str(row['证券代码']).zfill(6)
                sz_prev_map[code] = row['融资余额']

        # Columns: 证券代码, 证券简称, 融资买入额, 融资余额, 融券卖出量, 融券余量, 融券余额, 融资融券余额
        for _, row in df_sz.iterrows():
            code = str(row['证券代码']).zfill(6) # Ensure 6 digits
            if code in target_codes_pure:
                balance = row['融资余额']
                buy = row['融资买入额']
                
                # Calculate Net Buy: Balance_T - Balance_T-1
                net_buy = 0
                if code in sz_prev_map:
                    net_buy = balance - sz_prev_map[code]
                else:
                    # Fallback if no prev data? Maybe just use Buy? Or 0?
                    # Using Buy is wrong as it ignores repay.
                    # Best effort: use Buy if we really have to, typically repay exists.
                    # But actually without repay, net_buy is unknown.
                    # Let's set to 0 or leave it empty? User wants chart.
                    # Let's assume 0 if missing to avoid huge spikes.
                    net_buy = 0 
                
                results.append({
                    'code': code,
                    'name': row['证券简称'],
                    'margin_buy': buy,
                    'margin_balance': balance,
                    'margin_net_buy': net_buy, # Added
                    'margin_total': row['融资融券余额'],
                    'date': row['date'],
                    'market': 'sz'
                })

    # Process SSE
    if not df_sh.empty:
        # Columns: 信用交易日期, 标的证券代码, 标的证券简称, 融资余额, 融资买入额, 融资偿还额, 融券余量, 融券卖出量, 融券偿还量
        for _, row in df_sh.iterrows():
            code = str(row['标的证券代码']).zfill(6)
            if code in target_codes_pure:
                buy = row['融资买入额']
                repay = row['融资偿还额']
                net_buy = buy - repay
                
                results.append({
                    'code': code,
                    'name': row['标的证券简称'],
                    'margin_buy': buy,
                    'margin_balance': row['融资余额'],
                    'margin_net_buy': net_buy, # Added
                    'margin_total': row['融资余额'], # SSE might not have total column directly named same
                    'date': row['date'],
                    'market': 'sh'
                })
                
    return pd.DataFrame(results)

def fetch_foreign_flows(stock_list):
    """
    Fetch foreign holdings and fund flows.
    """
    print("Fetching Foreign Flows...")
    results = []
    
    # 1. Get Top Foreign Holdings (Market Wide) to check if our stocks are heavy
    # This might be slow to check one by one.
    # Let's check individual fund flow for all target stocks.
    
import concurrent.futures

def fetch_single_stock_flow(stock):
    code = stock['code']
    name = stock['name']
    
    # Strip prefix for akshare functions that don't want it
    code_pure = code[2:] if code.startswith(('sh', 'sz', 'bj')) else code
    
    try:
        # Fund Flow (Realtime/Daily)
        market = "sh" if code.startswith("sh") or code.startswith("6") else "sz"
        if code.startswith("bj") or code.startswith("4") or code.startswith("8"): market = "bj"
        
        df_flow = ak.stock_individual_fund_flow(stock=code_pure, market=market)
        
        latest_flow = 0
        latest_date = ""
        
        if df_flow is not None and not df_flow.empty:
            last_row = df_flow.iloc[-1]
            latest_flow = last_row['主力净流入-净额'] # Main force net inflow
            latest_date = last_row['日期']
            
        # Foreign Holding (Northbound)
        df_hold = ak.stock_hsgt_individual_em(symbol=code_pure)
        latest_holding = 0
        latest_holding_ratio = 0
        
        if df_hold is not None and not df_hold.empty:
            last_row = df_hold.iloc[-1]
            latest_holding = last_row['持股数量']
            latest_holding_ratio = last_row['持股数量占A股百分比']
            
        return {
            'code': code,
            'name': name,
            'flow_date': latest_date,
            'net_inflow': latest_flow,
            'foreign_holding': latest_holding,
            'foreign_ratio': latest_holding_ratio
        }
        
    except Exception as e:
        # print(f"Error fetching foreign/flow for {code}: {e}")
        return None

def fetch_foreign_flows(stock_list):
    """
    Fetch foreign holdings and fund flows.
    """
    print("Fetching Foreign Flows...")
    results = []
    total = len(stock_list)
    completed = 0
    
    # Increased workers to 20 for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_single_stock_flow, stock) for stock in stock_list]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
            
            completed += 1
            if completed % 10 == 0 or completed == total:
                print(f"Foreign/Flow Progress: {completed}/{total} stocks processed...", end='\r')
    
    print(f"\nForeign Flows Done. Got {len(results)} valid records.")        
    return pd.DataFrame(results)

def fetch_lhb_data(stock_list):
    """
    Check if stocks are on LHB today.
    """
    print("Fetching LHB Data...")
    today = datetime.now().strftime("%Y%m%d")
    
    # Try EM first
    df = None
    try:
        df = ak.stock_lhb_detail_em(start_date=today, end_date=today)
    except Exception as e:
        print(f"LHB EM Error: {e}")
        
    # Try Sina if EM fails or empty
    if df is None or df.empty:
        try:
            print("Trying Sina LHB...")
            df = ak.stock_lhb_detail_daily_sina(date=today)
        except Exception as e:
            print(f"LHB Sina Error: {e}")
            
    if df is None or df.empty:
        return pd.DataFrame()
        
    target_codes_pure = {s['code'][2:] if s['code'].startswith(('sh', 'sz', 'bj')) else s['code'] for s in stock_list}
    results = []
    
    # Normalize columns
    # EM: 代码, 名称, 上榜原因, 收盘价, 涨跌幅, 净买入额
    # Sina: 股票代码, 股票名称, 上榜理由, 收盘价, 涨跌幅, 净买入
    
    for _, row in df.iterrows():
        code = ""
        name = ""
        reason = ""
        close = 0
        pct_change = 0
        net_buy = 0
        
        if '代码' in row: code = str(row['代码'])
        elif '股票代码' in row: code = str(row['股票代码'])
        
        code = code.zfill(6)
        
        if code in target_codes_pure:
            if '名称' in row: name = row['名称']
            elif '股票名称' in row: name = row['股票名称']
            
            if '上榜原因' in row: reason = row['上榜原因']
            elif '上榜理由' in row: reason = row['上榜理由']
            
            if '收盘价' in row: close = row['收盘价']
            if '涨跌幅' in row: pct_change = row['涨跌幅']
            
            if '净买入额' in row: net_buy = row['净买入额']
            elif '净买入' in row: net_buy = row['净买入']
            
            results.append({
                'code': code,
                'name': name,
                'reason': reason,
                'close': close,
                'pct_change': pct_change,
                'net_buy': net_buy
            })

    return pd.DataFrame(results)

def fetch_market_margin_history(days=10):
    """
    Fetch total market margin balance history for the last N trading days.
    """
    print(f"Fetching Market Margin History ({days} days)...")
    
    today = datetime.now()
    # Look back 30 days to ensure we get enough trading days
    start_date = today - timedelta(days=days*3)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = today.strftime("%Y%m%d")
    
    # 1. Fetch SSE History (Batch)
    df_sh = pd.DataFrame()
    try:
        # SSE returns history in one call
        # Unit: Yuan (needs / 1e8)
        # Column: 融资余额
        df_sh = ak.stock_margin_sse(start_date=start_str, end_date=end_str)
        if df_sh is not None and not df_sh.empty:
             # Standardize Date column
             # Usually '信用交易日期' is int or str like 20240115
             df_sh['date'] = df_sh['信用交易日期'].astype(str)
             df_sh['sh_balance_yi'] = df_sh['融资余额'] / 100000000
    except Exception as e:
        print(f"SSE Valid History Check Error: {e}")
        # If batch fails, maybe fall back? But sse usually works.
    
    # 2. Fetch SZSE History (Loop)
    # SZSE summary by date
    # Unit: 100 Million (Yi)
    sz_history = []
    
    # We loop dates present in SSE or just loop calendar if SSE failed
    # Better to loop calendar range to be safe
    current_date = today
    dates_to_check = []
    
    # Generate dates backwards
    for i in range((today - start_date).days + 1):
        d = today - timedelta(days=i)
        dates_to_check.append(d.strftime("%Y%m%d"))
        
    for d_str in dates_to_check:
        try:
             # ak.stock_margin_szse returns summary for that date
             temp = ak.stock_margin_szse(date=d_str)
             if temp is not None and not temp.empty:
                 if '融资余额' in temp.columns:
                     val = temp['融资余额'].iloc[0] # Unit: Yi
                     sz_history.append({'date': d_str, 'sz_balance_yi': float(val)})
        except:
             # Date might be weekend or no data
             pass
             
    df_sz = pd.DataFrame(sz_history)
    
    # 3. Merge
    if df_sz.empty and df_sh.empty:
        return pd.DataFrame()
        
    # If one is empty, use the other? Or intersect?
    # Usually we want Total = SH + SZ.
    # We join on date.
    
    df_final = pd.DataFrame()
    if not df_sh.empty and not df_sz.empty:
        df_final = pd.merge(df_sh[['date', 'sh_balance_yi']], df_sz, on='date', how='inner')
        df_final['total_balance'] = df_final['sh_balance_yi'] + df_final['sz_balance_yi'] # Yi + Yi
    elif not df_sh.empty:
         # Only SH
         df_final = df_sh[['date', 'sh_balance_yi']].copy()
         df_final['total_balance'] = df_final['sh_balance_yi']
    elif not df_sz.empty:
         # Only SZ
         df_final = df_sz.copy()
         df_final['total_balance'] = df_final['sz_balance_yi']
         
    # Take last N days
    if not df_final.empty:
        df_final = df_final.sort_values('date', ascending=True)
        # Convert total back to Yuan for compatibility if needed? 
        # But report expects Yi. 
        # Run monitor saves it. Report reads it and divides by 1e8 again?
        # Let's check report code.
        # Report code: (df_market_margin['total_balance'] / 100000000).round(2)
        # So Report expects Yuan (Units).
        # My calculated 'total_balance' here is in Yi.
        # So I should multiply by 1e8 before returning, to keep consistent with "Margin Balance" usually being in Yuan.
        
        df_final['total_balance'] = df_final['total_balance'] * 100000000
        
        return df_final.tail(days)
        
    return pd.DataFrame()

def fetch_index_turnover_history(days=10):
    """
    Fetch turnover history for major indices (last N days).
    Returns DataFrame with columns: date, index_name, turnover_yi
    """
    print(f"Fetching Index Turnover History ({days} days)...")
    
    indices_map = {
        "上证50": "sh000016",
        "沪深300": "sh000300",
        "中证500": "sh000905",
        "中证1000": "sh000852",
        "中证2000": "csi932000" 
    }
    
    today = datetime.now()
    start_date = today - timedelta(days=days*4) # Look back more to be safe for 10 trading days
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = today.strftime("%Y%m%d")
    
    results = []
    
    for name, code in indices_map.items():
        try:
            # print(f"-> Fetching {name} ({code})...")
            df = ak.stock_zh_index_daily_em(symbol=code, start_date=start_str, end_date=end_str)
            
            # Fallback for CSI 2000
            if df.empty and "932000" in code:
                # print(f"   (Trying backup code sh932000...)")
                df = ak.stock_zh_index_daily_em(symbol="sh932000", start_date=start_str, end_date=end_str)
            
            if not df.empty:
                # Keep last N rows
                df_recent = df.tail(days).copy()
                
                # Process columns: date, amount (turnover)
                # date format from akshare usually YYYY-MM-DD or YYYYMMDD?
                # stock_zh_index_daily_em returns 'date' column like '2024-01-15'
                
                for _, row in df_recent.iterrows():
                    # amount is in Yuan, convert to Yi
                    # Check if amount is string or float
                    amt = float(row['amount']) if row['amount'] else 0
                    date_val = str(row['date']).replace("-", "")[:8] # Normalize to YYYYMMDD
                    
                    results.append({
                        'date': date_val,
                        'name': name,
                        'turnover_yi': round(amt / 100000000, 2)
                    })
                    
        except Exception as e:
            print(f"Index fetch error {name}: {e}")
            
    return pd.DataFrame(results)
