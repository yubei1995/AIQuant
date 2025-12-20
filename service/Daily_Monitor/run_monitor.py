import os
import pandas as pd
from datetime import datetime
from config import load_stock_list, NATIONAL_TEAM_ETFS
from data_fetcher import fetch_margin_data, fetch_foreign_flows, fetch_lhb_data, fetch_etf_shares
from generate_daily_report import generate_daily_report

def run_daily_monitor():
    print(f"Starting Daily Monitor at {datetime.now()}")
    
    # 1. Load Stock List
    stocks = load_stock_list()
    if not stocks:
        print("No stocks found.")
        return
        
    print(f"Monitoring {len(stocks)} stocks.")
    
    # 2. Fetch Data
    # Margin
    df_margin = fetch_margin_data(stocks)
    
    # Foreign & Flows
    df_foreign = fetch_foreign_flows(stocks)
    
    # LHB
    df_lhb = fetch_lhb_data(stocks)
    
    # ETF
    df_etf = fetch_etf_shares(NATIONAL_TEAM_ETFS)
    
    # 3. Save Results
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    date_str = datetime.now().strftime("%Y%m%d")
    
    if not df_margin.empty:
        path = os.path.join(output_dir, f"margin_data_{date_str}.csv")
        df_margin.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved Margin Data to {path}")
        
    if not df_foreign.empty:
        path = os.path.join(output_dir, f"foreign_flow_{date_str}.csv")
        df_foreign.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved Foreign Flow Data to {path}")
        
    if not df_lhb.empty:
        path = os.path.join(output_dir, f"lhb_data_{date_str}.csv")
        df_lhb.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved LHB Data to {path}")
        
    if not df_etf.empty:
        path = os.path.join(output_dir, f"etf_shares_{date_str}.csv")
        df_etf.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved ETF Data to {path}")
        
    # 4. Generate Report
    print("Generating HTML Report...")
    generate_daily_report(date_str)
        
    print("Daily Monitor Completed.")

if __name__ == "__main__":
    run_daily_monitor()
