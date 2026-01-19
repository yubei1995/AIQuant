import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def check_api():
    today = datetime.now()
    # Find a recent trading day (e.g. last Friday if today is weekend)
    # 2026/01/18 is Sunday. 2026/01/16 is Friday.
    date_str = '20250116' # Use a known past valid date to be safe for testing API structure, or relatively recent. 
    # But wait, user is in 2026. I should use 2026 dates if available? 
    # If the system time is 2026, maybe the current date is simulating.
    # I'll use a date relative to "now".
    
    # Try to find a working date
    for i in range(5):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        print(f"Checking date: {d}")
        try:
            print("--- SZSE ---")
            df_sz = ak.stock_margin_szse(date=d)
            if df_sz is not None and not df_sz.empty:
                print(f"Shape: {df_sz.shape}")
                print(f"Columns: {df_sz.columns.tolist()}")
                print(f"First row: {df_sz.iloc[0].to_dict()}")
                # Check if it looks like summary or detail
                if len(df_sz) > 100:
                    print("Looks like DETAIL data (many rows).")
                    if '融资余额' in df_sz.columns:
                        total = df_sz['融资余额'].sum()
                        print(f"Calculated Total Margin Balance: {total}")
                else:
                    print("Looks like SUMMARY data.")
                
            print("--- SSE ---")
            df_sh = ak.stock_margin_sse(date=d)
            if df_sh is not None and not df_sh.empty:
                 print(f"Shape: {df_sh.shape}")
                 print(df_sh.head())
            
            if df_sz is not None and not df_sz.empty:
                break
        except Exception as e:
            print(f"Error for {d}: {e}")

if __name__ == "__main__":
    check_api()
