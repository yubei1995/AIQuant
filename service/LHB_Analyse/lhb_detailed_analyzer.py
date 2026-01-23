import sys
import os
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
import concurrent.futures
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.utils.lhb_config_loader import load_lhb_config
try:
    from generate_lhb_report import generate_html
except ImportError:
    # Try importing assuming run from project root or service dir
    sys.path.append(os.path.dirname(__file__))
    from generate_lhb_report import generate_html

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_lhb_stock_list(date_str):
    """Fetch the list of stocks on LHB for a given date."""
    print(f"Fetching LHB summary for {date_str}...")
    try:
        df = ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
        return df
    except Exception as e:
        print(f"Error fetching LHB summary: {e}")
        return pd.DataFrame()

def fetch_stock_details(symbol, date_str):
    """Fetch detailed buyer/seller for a stock."""
    # print(f"Fetching details for {symbol}...")
    try:
        # Fetch Top 5 Buyers
        df_buy = ak.stock_lhb_stock_detail_em(symbol=symbol, date=date_str, flag="买入")
        # Fetch Top 5 Sellers
        df_sell = ak.stock_lhb_stock_detail_em(symbol=symbol, date=date_str, flag="卖出")
        return df_buy, df_sell
    except Exception as e:
        # print(f"Error fetching details for {symbol}: {e}")
        return None, None

def fetch_total_market_turnover(date_str):
    """
    Fetch total market turnover (SH + SZ) for a specific date.
    Returns: float (Amount in Yuan) or 0
    """
    try:
        # We need ShangZheng (sh000001) + ShenZheng (sz399001)
        # Using stock_zh_index_daily_em
        indices = ["sh000001", "sz399001"]
        total_turnover = 0.0
        found_cnt = 0
        
        for code in indices:
            try:
                # Fetch a range to avoid single-day issues
                start_dt = datetime.strptime(date_str, "%Y%m%d") - timedelta(days=10)
                start_s = start_dt.strftime("%Y%m%d")
                
                df = ak.stock_zh_index_daily_em(symbol=code, start_date=start_s, end_date=date_str)
                if not df.empty:
                    # Try to match the exact date
                    # Ensure date column is string
                    df['date'] = df['date'].astype(str)
                    target_d_hyphen = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
                    
                    # Check for YYYYMMDD or YYYY-MM-DD
                    mask = df['date'].isin([date_str, target_d_hyphen])
                    if mask.any():
                        val = float(df[mask].iloc[0]['amount'])
                        total_turnover += val
                        found_cnt += 1
            except:
                pass
                
        if found_cnt > 0:
            return total_turnover
            
    except Exception as e:
        print(f"Error fetching market turnover: {e}")
        
    return 0.0

def analyze_daily_lhb(date_str, config_path):
    """
    Main analysis function.
    """
    # 1. Load Config
    print("Loading LHB configuration...")
    # New loader returns (exact_map, fuzzy_rules)
    result = load_lhb_config(config_path)
    
    # Handle both tuple (new) and dict (legacy) just in case
    if isinstance(result, tuple):
        branch_map, fuzzy_rules = result
    else:
        branch_map = result
        fuzzy_rules = []
    
    # 2. Get Stock List
    df_summary = fetch_lhb_stock_list(date_str)
    if df_summary is None or df_summary.empty:
        print("No LHB data found for this date.")
        return
    
    print(f"Summary columns: {df_summary.columns.tolist()}")
    if not df_summary.empty:
        print(f"First summary row: {df_summary.iloc[0].to_dict()}")

    stocks = []
    if '代码' in df_summary.columns:
        stocks = df_summary['代码'].astype(str).unique().tolist()
    elif '股票代码' in df_summary.columns:
        stocks = df_summary['股票代码'].astype(str).unique().tolist()
    
    # Save Summary to CSV for Daily Monitor use
    summary_file = os.path.join(OUTPUT_DIR, 'lhb_latest_summary.csv')
    try:
        df_summary.to_csv(summary_file, index=False, encoding='utf-8-sig')
        print(f"LHB Summary saved to: {summary_file}")
    except Exception as e:
        print(f"Error saving LHB summary: {e}")
        
    print(f"Found {len(stocks)} stocks on LHB.")
    
    # 3. Fetch Details (Concurrent)
    lhb_details = []
    
    print("Fetching detailed seat data...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_stock = {executor.submit(fetch_stock_details, s, date_str): s for s in stocks}
        
        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                df_buy, df_sell = future.result()
                
                if df_buy is not None and not df_buy.empty:
                    df_buy['side'] = 'buy'
                    df_buy['stock_code'] = stock
                    lhb_details.append(df_buy)
                    
                if df_sell is not None and not df_sell.empty:
                    df_sell['side'] = 'sell'
                    df_sell['stock_code'] = stock
                    lhb_details.append(df_sell)
                    
            except Exception as e:
                print(f"Failed to process {stock}: {e}")
                
    if not lhb_details:
        print("No detailed data retrieved.")
        return

    df_details = pd.concat(lhb_details, ignore_index=True)
    
    # 4. Process & Tag Data
    
    # [Fix] Deduplicate: A branch might appear in both Buy5 and Sell5 for the same stock
    # We remove duplicates based on Stock Code and Branch Name to avoid double counting
    
    # Find the branch column name first for deduplication
    branch_col = None
    for c in ['交易营业部名称', '营业部名称', '席位名称', '名称']:
        if c in df_details.columns:
            branch_col = c
            break
            
    if branch_col:
        before_len = len(df_details)
        df_details = df_details.drop_duplicates(subset=['stock_code', branch_col])
        after_len = len(df_details)
        if before_len > after_len:
            print(f"Removed sequence duplicates: {before_len - after_len} rows (overlapping Buy/Sell seats).")

    # Initialize Counters
    stats = {
        '网红游资': 0.0,
        '高频量化席位': 0.0,
        '机构': 0.0,
        '外资': 0.0,
        '其他游资': 0.0,
        'Total_LHB_Turnover': 0.0 # From summary
    }
    
    def parse_amount(val):
        if pd.isna(val):
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # Remove commas if present
            val = val.replace(',', '')
            try:
                return float(val)
            except:
                return 0.0
        return 0.0

    # Calculate Total LHB Turnover
    # Summary columns usually include '龙虎榜成交额' or '成交额'
    if '龙虎榜成交额' in df_summary.columns:
         stats['Total_LHB_Turnover'] = df_summary['龙虎榜成交额'].apply(parse_amount).sum()
    elif '成交额' in df_summary.columns:
         stats['Total_LHB_Turnover'] = df_summary['成交额'].apply(parse_amount).sum()
    
    print("Classifying seat data...")
    print(f"Detail columns: {df_details.columns.tolist()}")
    if not df_details.empty:
        branch_sample = df_details.iloc[0].to_dict()
        # Find the correct key for branch
        for k in ['交易营业部名称', '营业部名称', '席位名称', '名称']:
            if k in branch_sample:
                print(f"Sample branch name: '{branch_sample[k]}'")
                break

    # Create a map for stock name
    code_to_name = {}
    if '代码' in df_summary.columns and '名称' in df_summary.columns:
        code_to_name = df_summary.set_index('代码')['名称'].to_dict()
    elif '股票代码' in df_summary.columns and '股票名称' in df_summary.columns:
        code_to_name = df_summary.set_index('股票代码')['股票名称'].to_dict()

    # Normalize columns if necessary
    col_map = {
        '交易营业部名称': 'branch',
        '营业部名称': 'branch',
        '席位名称': 'branch',
        '名称': 'branch',
        '买入金额': 'buy',
        '买入金额(万)': 'buy',
        '卖出金额': 'sell',
        '卖出金额(万)': 'sell'
    }
    
    # 1. Save RAW Details CSV
    try:
        # Add stock name to details if missing
        if 'stock_name' not in df_details.columns:
             df_details['stock_name'] = df_details['stock_code'].astype(str).map(code_to_name).fillna('')
             
        raw_detail_file = os.path.join(OUTPUT_DIR, 'lhb_latest_raw_detail.csv')
        df_details.to_csv(raw_detail_file, index=False, encoding='utf-8-sig')
        print(f"Raw details saved to: {raw_detail_file}")
    except Exception as e:
        print(f"Error saving raw details: {e}")
    
    # We aggregate NET BUY for each category.
    # Note: LHB details usually List Top 5 Buy and Top 5 Sell.
    # A seat might appear on Buy side (with buy_amt, and maybe sell_amt=0 or small)
    # A seat might appear on Sell side.
    # We should sum (Buy Amount - Sell Amount) for each record found in details.
    
    total_net_buy_analyzed = 0.0
    # Change alias_stats structure to store buy/sell/net
    alias_stats = {} 
    alias_category_map = {}
    
    # Collection for Granular Alias/Branch CSV and JSON Display
    granular_records = []
    
    # Store all enriched rows for JSON output (Stock -> Branches)
    all_enriched_rows = []

    for _, row in df_details.iterrows():
        # Identify Branch Column
        branch = None

        for c in ['交易营业部名称', '营业部名称', '席位名称', '名称']:
            if c in row:
                branch = str(row[c]).strip()
                break
        
        if not branch:
            continue
            
        # Check amount columns
        buy_amt = 0.0
        sell_amt = 0.0
        
        # Handle variations in amount columns
        if '买入金额' in row:
             buy_amt = parse_amount(row['买入金额'])
        elif '买入金额(万)' in row: 
             buy_amt = parse_amount(row['买入金额(万)']) * 10000

        if '卖出金额' in row:
            sell_amt = parse_amount(row['卖出金额'])
        elif '卖出金额(万)' in row:
            sell_amt = parse_amount(row['卖出金额(万)']) * 10000
            
        net = buy_amt - sell_amt
        total_net_buy_analyzed += net
        
        # Classification Logic
        category = "其他游资" # Default
        alias = None
        rule_type = "Unmatched"
        
        # 1. Exact Match
        if branch in branch_map:
            category = branch_map[branch]['category']
            alias = branch_map[branch].get('alias')
            rule_type = "Exact"
        else:
            # Smart Matching: Check if Config string is contained in Actual Branch string
            # Priority: Fuzzy Rules (Explicit) > Substring Match > Exact
            
            # 2. Fuzzy Match (XML Configured - Explicit 'contains')
            found = False
            for rule in fuzzy_rules:
                if rule['match'] == 'contains':
                    # Support multi-keyword matching (space separated)
                    # e.g. Pattern "中信证券 上海分公司" -> matches "中信证券股份有限公司上海分公司"
                    keywords = rule['pattern'].split()
                    if all(k in branch for k in keywords):
                        category = rule['category']
                        alias = rule.get('alias')
                        found = True
                        rule_type = "Fuzzy(XML)"
                        break
            
            if not found:
                 # 3. Implicit Substring Match (Try to match keys from exact_map as substrings)
                 for k, v in branch_map.items():
                     if k in branch:
                         category = v['category']
                         alias = v.get('alias')
                         found = True
                         rule_type = "ImplicitSubstring"
                         # print(f"Implicit Match: {k} in {branch}")
                         break
            
            if not found:
                pass
        
        # Add to enriched list
        all_enriched_rows.append({
            'stock_code': row.get('stock_code', ''),
            'stock_name': row.get('stock_name', ''),
            'branch': branch,
            'alias': alias if alias else '',
            'category': category if category != "其他游资" else '',
            'buy': buy_amt,
            'sell': sell_amt,
            'net': net
        })
        
        # Accumulate
        if category in stats:
            stats[category] += net
        else:
            # If the category from map is new (e.g. from XML that wasn't in initial stats dict)
            # Add to it.
            stats[category] = stats.get(category, 0.0) + net

        # Accumulate Alias Stats & Save Granular Record
        if alias:
            if alias not in alias_stats:
                alias_stats[alias] = {'buy': 0.0, 'sell': 0.0, 'net': 0.0}
            
            alias_stats[alias]['buy'] += buy_amt
            alias_stats[alias]['sell'] += sell_amt
            alias_stats[alias]['net'] += net
            
            if alias not in alias_category_map:
                alias_category_map[alias] = category
            
            # 2. Store Granular Record for Step 2 CSV
            granular_records.append({
                'date': date_str,
                'stock_code': row.get('stock_code', ''),
                'stock_name': row.get('stock_name', ''),
                'alias': alias,
                'category': category,
                'branch_name': branch,
                'buy_amt': buy_amt,
                'sell_amt': sell_amt,
                'net_amt': net,
                'rule_type': rule_type
            })
            
    # Save Granular Alias Details
    try:
        if granular_records:
            alias_detail_file = os.path.join(OUTPUT_DIR, 'lhb_latest_alias_detail.csv')
            pd.DataFrame(granular_records).to_csv(alias_detail_file, index=False, encoding='utf-8-sig')
            print(f"Granular alias details saved to: {alias_detail_file}")
    except Exception as e:
        print(f"Error saving alias details: {e}")

    # 3. Save Structured JSON for Report Groups
    try:
        if all_enriched_rows:
            import json
            df_enriched = pd.DataFrame(all_enriched_rows)
            # Group by stock
            stock_groups = []
            
            # Get unique stocks
            stocks = df_enriched['stock_code'].unique()
            
            for code in stocks:
                df_s = df_enriched[df_enriched['stock_code'] == code]
                if df_s.empty:
                    continue
                    
                s_name = df_s.iloc[0]['stock_name']
                # Try to get extra info from summary list if possible
                
                # Sort branches by absolute net amount desc
                df_s['abs_net'] = df_s['net'].abs()
                df_s = df_s.sort_values('abs_net', ascending=False)
                
                branches = []
                total_net = 0.0
                for _, r in df_s.iterrows():
                    branches.append({
                        'branch': r['branch'],
                        'alias': r['alias'],
                        'category': r['category'],
                        'buy': r['buy'],
                        'sell': r['sell'],
                        'net': r['net']
                    })
                    total_net += r['net']
                
                stock_groups.append({
                    'code': code,
                    'name': s_name,
                    'net_buy': total_net,
                    'branches': branches
                })
            
            # Sort stocks by Net Buy Desc
            stock_groups.sort(key=lambda x: x['net_buy'], reverse=True)
            
            json_file = os.path.join(OUTPUT_DIR, 'lhb_latest_stock_map.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(stock_groups, f, ensure_ascii=False, indent=2)
            print(f"Stock details map saved to: {json_file}")
            
    except Exception as e:
        print(f"Error saving stock map json: {e}")
            
    # "Other Hot Money" Logic:
    # "（龙虎榜总的买入卖出净买入减去网红游资、机构、量化、外资各个分项）"
    # Wait, the details only cover Top 5 Buyers/Sellers (~10-20% of turnover).
    # Does "Total LHB Net Buy" mean the sum of ALL Top 5, or the stock's total net buy?
    # Usually we can only analyze the seats we see (Top 5).
    # So "Total Analyzed Net Buy" = Sum of Net Buy of all rows in Detail DF.
    # Then "Other" = Total Analyzed - (Hot + Quant + Inst + Foreign).
    
    known_net_buy = 0.0
    for k, v in stats.items():
        if k in ['网红游资', '高频量化席位', '机构', '外资']:
            known_net_buy += v
            
    stats['其他游资'] = total_net_buy_analyzed - known_net_buy

    # Fetch Total Market Turnover
    market_turnover = fetch_total_market_turnover(date_str)

    # Format for output
    final_row = {
        'date': date_str,
        'hot_money_net': stats.get('网红游资', 0),
        'quant_net': stats.get('高频量化席位', 0),
        'inst_net': stats.get('机构', 0),
        'foreign_net': stats.get('外资', 0),
        'other_net': stats.get('其他游资', 0),
        'total_lhb_turnover': stats.get('Total_LHB_Turnover', 0),
        'total_market_turnover': market_turnover
    }
    
    # Save Alias History
    if alias_stats:
        alias_history_file = os.path.join(OUTPUT_DIR, 'lhb_alias_history.csv')
        daily_alias_data = []
        for alias, info in alias_stats.items():
            daily_alias_data.append({
                'date': date_str,
                'alias': alias,
                'category': alias_category_map.get(alias, 'Unknown'),
                'buy': info['buy'],
                'sell': info['sell'],
                'net_buy': info['net']
            })
        
        df_alias_new = pd.DataFrame(daily_alias_data)
        if os.path.exists(alias_history_file):
            try:
                df_hist = pd.read_csv(alias_history_file)
                # Remove existing for same date
                df_hist = df_hist[df_hist['date'].astype(str) != date_str]
                df_alias_final = pd.concat([df_hist, df_alias_new], ignore_index=True)
            except Exception as e:
                print(f"Error reading alias history: {e}. Overwriting.")
                df_alias_final = df_alias_new
        else:
            df_alias_final = df_alias_new
            
        df_alias_final.to_csv(alias_history_file, index=False)
        print("Alias analysis saved to", alias_history_file)

    # Save to history
    history_file = os.path.join(OUTPUT_DIR, 'lhb_analysis_history.csv')
    df_new = pd.DataFrame([final_row])
    
    if os.path.exists(history_file):
        df_hist = pd.read_csv(history_file)
        # Remove existing for same date
        df_hist = df_hist[df_hist['date'].astype(str) != date_str]
        df_combined = pd.concat([df_hist, df_new], ignore_index=True)
    else:
        df_combined = df_new
        
    df_combined.to_csv(history_file, index=False)
    print("Analysis saved to", history_file)
    print(df_new.T)

if __name__ == "__main__":
    # Check for history file
    history_file = os.path.join(OUTPUT_DIR, 'lhb_analysis_history.csv')
    
    # default target is today
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = datetime.now().strftime("%Y%m%d")

    config_path = os.path.join(os.path.dirname(__file__), '../../data/lhb_config.xml')

    # If history is missing, we perform a backfill for the last N days (e.g., 5 days) to provide some trend context
    # This allows stateless runs (GitHub Actions) without needing to commit history back to repo.
    if not os.path.exists(history_file):
        print("History file not found. Starting backfill for trend context (last 5 days)...")
        # Generate dates
        backfill_days = 5
        curr = datetime.strptime(target_date, "%Y%m%d")
        
        # Simple loop backwards
        dates_to_run = []
        for i in range(backfill_days, 0, -1):
            d = curr - timedelta(days=i)
            dates_to_run.append(d.strftime("%Y%m%d"))
        
        # Run backfill
        for d in dates_to_run:
            print(f"--- Backfill Analysis for {d} ---")
            try:
                # We catch errors here so one missing day doesn't stop the flow
                analyze_daily_lhb(d, config_path)
            except Exception as e:
                print(f"Skipping backfill for {d}: {e}")

    # Always run for the target date (Detailed analysis)
    print(f"--- Running Main Analysis for {target_date} ---")
    analyze_daily_lhb(target_date, config_path)
    
    # Generate HTML Report
    if os.path.exists(history_file):
        print("Generating HTML report...")
        try:
            df_hist = pd.read_csv(history_file)
            generate_html(df_hist)
        except Exception as e:
            print(f"Error generating HTML report: {e}")
