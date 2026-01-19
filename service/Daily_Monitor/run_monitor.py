import os
import pandas as pd
from datetime import datetime
from config import load_stock_list
from data_fetcher import fetch_margin_data, fetch_foreign_flows, fetch_lhb_data, fetch_market_margin_history, fetch_index_turnover_history
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
    
    if not df_margin.empty:
        latest_date = df_margin['date'].max()
        print(f"Latest Margin Data Date: {latest_date}")
    
    # Process Margin by Block
    if not df_margin.empty:
        # Create a map of code to block
        code_block_map = {}
        for s in stocks:
            # Map simple code to block
            simple_code = s['code'][2:] if s['code'].startswith(('sh', 'sz', 'bj')) else s['code']
            code_block_map[simple_code] = s['block']
            
        df_margin['block'] = df_margin['code'].map(code_block_map)
        
        # Group by block and sum margin_net_buy and margin_balance
        df_block_margin = df_margin.groupby('block')[['margin_net_buy', 'margin_balance']].sum().reset_index()
        df_block_margin.columns = ['block_name', 'margin_net_buy_sum', 'margin_balance_sum']
        
        # Calculate Ratio
        # Prev Balance = Current Balance - Net Buy
        df_block_margin['margin_balance_prev_sum'] = df_block_margin['margin_balance_sum'] - df_block_margin['margin_net_buy_sum']
        # Ratio = Net Buy / Prev Balance * 100
        df_block_margin['net_buy_ratio'] = df_block_margin.apply(
            lambda row: (row['margin_net_buy_sum'] / row['margin_balance_prev_sum'] * 100) if row['margin_balance_prev_sum'] != 0 else 0, 
            axis=1
        )
        
        # Load Ranking from Block Analysis if available
        # service/Daily_Monitor -> service -> AIQuant
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        block_stats_path = os.path.join(project_root, "service", "Block_Analyse", "output", "block_statistics.csv")
        
        if os.path.exists(block_stats_path):
            try:
                df_ranking = pd.read_csv(block_stats_path)
                # Assumes '细分板块' is column name or whatever Block Analysis uses
                if '细分板块' in df_ranking.columns:
                     # Create a categorical type based on ranking
                     ordered_blocks = df_ranking['细分板块'].tolist()
                     df_block_margin['block_name'] = pd.Categorical(df_block_margin['block_name'], categories=ordered_blocks, ordered=True)
                     # Sort
                     df_block_margin = df_block_margin.sort_values('block_name')
                else:
                    print("Block ranking column not found, using default sort.")
            except Exception as e:
                print(f"Error loading block ranking: {e}")
        
        # Save Block Margin Data
        block_margin_path = os.path.join(os.path.dirname(__file__), "output", "block_margin.csv")
        df_block_margin.to_csv(block_margin_path, index=False, encoding='utf-8-sig')
        print(f"Saved Block Margin Data to {block_margin_path}")

    # Foreign & Flows
    df_foreign = fetch_foreign_flows(stocks)
    
    # LHB
    df_lhb = fetch_lhb_data(stocks)
    
    # Market Margin History (Total Balance for last 10 days)
    df_market_margin = fetch_market_margin_history(days=10)

    # Index Turnover History (Last 10 days)
    df_index_turnover = fetch_index_turnover_history(days=10)
    
    # 3. Save Results
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    date_str = datetime.now().strftime("%Y%m%d")
    
    if not df_margin.empty:
        path = os.path.join(output_dir, "margin_data.csv")
        df_margin.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved Margin Data to {path}")
        
    if not df_foreign.empty:
        path = os.path.join(output_dir, "foreign_flow.csv")
        df_foreign.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved Foreign Flow Data to {path}")
        
    if not df_lhb.empty:
        path = os.path.join(output_dir, "lhb_data.csv")
        df_lhb.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved LHB Data to {path}")

    if not df_market_margin.empty:
        path = os.path.join(output_dir, "market_margin_history.csv")
        df_market_margin.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved Market Margin History to {path}")

    if not df_index_turnover.empty:
        path = os.path.join(output_dir, "index_turnover_history.csv")
        df_index_turnover.to_csv(path, index=False, encoding='utf-8-sig')
        print(f"Saved Index Turnover History to {path}")
        
    # 4. Generate Report
    print("Generating HTML Report...")
    generate_daily_report(output_dir, date_str)
        
    print("Daily Monitor Completed.")

if __name__ == "__main__":
    run_daily_monitor()
