from modules.massive_data_layer import MassiveDataLayer
import os

# Ticker list extracted from Nifty 200 CSV (cleaned to strings)
NIFTY_200_SYMBOLS = [
    "360ONE", "ABB", "APLAPOLLO", "AUBANK", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", 
    "ADANIPOWER", "ATGL", "ABCAPITAL", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", 
    "ASTRAL", "AUROPHARMA", "DMART", "AXISBANK", "BSE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", 
    "BAJAJHLDNG", "BANKBARODA", "BANKINDIA", "BDL", "BEL", "BHARATFORG", "BHEL", "BPCL", "BHARTIARTL", 
    "BIOCON", "BLUESTARCO", "BOSCHLTD", "BRITANNIA", "CGPOWER", "CANBK", "CHOLAFIN", "CIPLA", 
    "COALINDIA", "COCHINSHIP", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CUMMINSIND", "DLF", 
    "DABUR", "DIVISLAB", "DIXON", "DRREDDY", "EICHERMOT", "EXIDEIND", "NYKAA", "FEDERALBNK", 
    "FORTIS", "GAIL", "GMRAIRPORT", "GLENMARK", "GODFRYPHLP", "GODREJCP", "GODREJPROP", "GRASIM", 
    "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HAVELLS", "HEROMOTOCO", "HINDALCO", "HAL", 
    "HINDPETRO", "HINDUNILVR", "HINDZINC", "HUDCO", "ICICIBANK", "ICICIGI", "IDFCFIRSTB", "ITC", 
    "INDIANB", "INDHOTEL", "IOC", "IRCTC", "IRFC", "IREDA", "INDUSTOWER", "INDUSINDBK", "NAUKRI", 
    "INFY", "INDIGO", "JSWENERGY", "JSWSTEEL", "JINDALSTEL", "JIOFIN", "JUBLFOOD", "KEI", "KPITTECH", 
    "KALYANKJIL", "KOTAKBANK", "LTF", "LICHSGFIN", "LTM", "LT", "LAURUSLABS", "LODHA", "LUPIN", 
    "MRF", "M&MFIN", "M&M", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "MOTILALOFS", 
    "MPHASIS", "MCX", "MUTHOOTFIN", "NHPC", "NMDC", "NTPC", "NATIONALUM", "NESTLEIND", "OBEROIRLTY", 
    "ONGC", "OIL", "PAYTM", "OFSS", "POLICYBZR", "PIIND", "PAGEIND", "PATANJALI", "PERSISTENT", 
    "PHOENIXLTD", "PIDILITIND", "POLYCAB", "PFC", "POWERGRID", "PRESTIGE", "PNB", "RECLTD", "RADICO", 
    "RVNL", "RELIANCE", "SBICARD", "SBILIFE", "SRF", "MOTHERSON", "SHREECEM", "SHRIRAMFIN", "SIEMENS", 
    "SOLARINDS", "SBIN", "SAIL", "SUNPHARMA", "SUPREMEIND", "SUZLON", "TVSMOTOR", "TATACOMM", "TCS", 
    "TATACONSUM", "TATAELXSI", "TATAINVEST", "TATAPOWER", "TATASTEEL", "TECHM", "TITAN", "TORNTPHARM", 
    "TRENT", "TIINDIA", "UPL", "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "VBL", "VEDL", "IDEA", "VOLTAS", 
    "WIPRO", "YESBANK", "ZYDUSLIFE"
]

# Note: Some tickers may fail if yfinance symbol doesn't match exactly.
# For example BAJAJ-AUTO, M&M, M&MFIN, GMRAIRPORT (GMRINFRA)

if __name__ == '__main__':
    # Limit to a smaller subset for the initial run to check performance/status
    subset = NIFTY_200_SYMBOLS[:50] # Taking first 50 as a starter
    
    dl = MassiveDataLayer(NIFTY_200_SYMBOLS)
    dl.bulk_fetch_1m(max_workers=10) # Using 10 parallel threads
    
    # Save Status Report
    report = dl.get_status_report()
    print(report)
    
    with open("data_status.txt", "w") as f:
        f.write(report)
    
    print("\n✅ data_status.txt updated.")
