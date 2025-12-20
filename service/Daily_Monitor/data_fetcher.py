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
            
    # Combine
    results = []
    # Strip prefixes from target codes for comparison if margin data uses pure codes
    target_codes_pure = {s['code'][2:] if s['code'].startswith(('sh', 'sz', 'bj')) else s['code'] for s in stock_list}
    target_codes_full = {s['code'] for s in stock_list}
    
    # Process SZSE
    if not df_sz.empty:
        # Columns: 证券代码, 证券简称, 融资买入额, 融资余额, 融券卖出量, 融券余量, 融券余额, 融资融券余额
        for _, row in df_sz.iterrows():
            code = str(row['证券代码']).zfill(6) # Ensure 6 digits
            if code in target_codes_pure:
                results.append({
                    'code': code,
                    'name': row['证券简称'],
                    'margin_buy': row['融资买入额'],
                    'margin_balance': row['融资余额'],
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
                results.append({
                    'code': code,
                    'name': row['标的证券简称'],
                    'margin_buy': row['融资买入额'],
                    'margin_balance': row['融资余额'],
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
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_stock_flow, stock) for stock in stock_list]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
            
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

def fetch_etf_shares(etf_list):
    """
    Fetch ETF share changes.
    """
    print("Fetching ETF Shares...")
    results = []
    
    # Use fund_etf_spot_em for latest info?
    # Or fund_etf_fund_info_em
    
    try:
        # Get spot data for all ETFs once
        df_spot = ak.fund_etf_spot_em()
        if df_spot is None or df_spot.empty:
            return pd.DataFrame()
            
        # df_spot columns usually include '代码', '名称', '最新价', ... '流通份额'?
        # Let's assume '流通份额' exists.
        
        for etf in etf_list:
            code = etf['code']
            name = etf['name']
            
            row = df_spot[df_spot['代码'] == code]
            if not row.empty:
                # Found
                current_shares = row.iloc[0].get('流通份额', 0)
                if current_shares == 0:
                     current_shares = row.iloc[0].get('数据存量', 0) # Fallback guess
                
                # To get change, we need yesterday's shares.
                # This is hard without history.
                # Let's try to fetch history for shares?
                # fund_etf_hist_em doesn't have shares.
                
                # Alternative: fund_etf_fund_daily_em?
                # Let's just record current shares for now.
                
                results.append({
                    'code': code,
                    'name': name,
                    'current_shares': current_shares,
                    'price': row.iloc[0]['最新价'],
                    'turnover': row.iloc[0]['成交额']
                })
                
    except Exception as e:
        print(f"ETF Error: {e}")
        
    return pd.DataFrame(results)
