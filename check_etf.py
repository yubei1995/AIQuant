import akshare as ak
import pandas as pd
import sys

# Set encoding to utf-8 for stdout
sys.stdout.reconfigure(encoding='utf-8')

print("Fetching ETF Spot...")
try:
    df = ak.fund_etf_spot_em()
    if df is not None and not df.empty:
        print("Columns:", df.columns.tolist())
        print("First row:", df.iloc[0].to_dict())
    else:
        print("ETF data is empty.")
except Exception as e:
    print(f"Error: {e}")
