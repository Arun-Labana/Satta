#!/usr/bin/env python3
"""
BSE API client module.
Handles BSE announcements, EOD data downloads, and stock price caching.
"""

from datetime import datetime, timedelta, timezone
import threading
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    # Fallback for Python < 3.9 or systems without zoneinfo
    try:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
    except ImportError:
        # Manual IST offset (UTC+5:30) as last resort
        IST = timezone(timedelta(hours=5, minutes=30))

# Global dictionary for BSE stock prices (symbol -> closing_price)
BSE_STOCK_PRICES = {}


def get_bse_announcements_url():
    """Generate BSE announcements URL with today's date in IST"""
    # Get current time in IST (Indian Standard Time, UTC+5:30)
    # datetime.now() works with ZoneInfo, datetime.timezone, and pytz timezone objects
    now_ist = datetime.now(IST)
    today = now_ist.strftime('%Y%m%d')
    return f'https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&strCat=Company+Update&strPrevDate={today}&strScrip=&strSearch=P&strToDate={today}&strType=C&subcategory=Award+of+Order+%2F+Receipt+of+Order'


def download_bse_eod_data():
    """Download BSE end-of-day data file and return dictionary of symbol -> closing_price
    Handles weekends and public holidays by trying previous trading days.
    Stops and returns immediately when valid data is found.
    Uses the correct BSE URL format: BhavCopy_BSE_CM_0_0_0_YYYYMMDD_F_0000.CSV
    """
    global BSE_STOCK_PRICES
    
    try:
        import requests
        import pandas as pd
        
        # Get current time in IST (Indian Standard Time, UTC+5:30)
        # datetime.now() works with ZoneInfo, datetime.timezone, and pytz timezone objects
        today = datetime.now(IST)
        max_days_back = 15
        
        print(f"[BSE EOD] Searching for last trading day (checking up to {max_days_back} days back)...")
        
        for day_offset in range(1, max_days_back + 1):
            check_date = today - timedelta(days=day_offset)
            weekday = check_date.weekday()
            
            # Skip weekends (Saturday=5, Sunday=6)
            if weekday >= 5:
                continue
            
            date_display = check_date.strftime('%Y-%m-%d (%A)')
            date_str = check_date.strftime('%Y%m%d')
            
            # BSE bhavcopy URL format: BhavCopy_BSE_CM_0_0_0_YYYYMMDD_F_0000.CSV
            file_name = f"BhavCopy_BSE_CM_0_0_0_{date_str}_F_0000.CSV"
            url = f"https://www.bseindia.com/download/BhavCopy/Equity/{file_name}"
            
            print(f"[BSE EOD] Checking {date_display}...")
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
                
                # Download the CSV file
                response = requests.get(url, headers=headers, stream=True, timeout=30)
                response.raise_for_status()
                
                # Parse CSV using pandas (more reliable)
                import io
                df = pd.read_csv(io.StringIO(response.text))
                
                # Create dictionary: symbol -> closing price
                # BSE CSV columns: TckrSymb (symbol), ClsPric (closing price)
                stock_prices = {}
                
                if 'TckrSymb' in df.columns and 'ClsPric' in df.columns:
                    for _, row in df.iterrows():
                        symbol = str(row.get('TckrSymb', '')).strip().upper()
                        close_price = row.get('ClsPric', 0)
                        
                        if symbol and close_price:
                            try:
                                closing_price = float(close_price)
                                if closing_price > 0:
                                    stock_prices[symbol] = closing_price
                            except (ValueError, TypeError):
                                continue
                    
                    # Validate we got reasonable data
                    if len(df) > 1000 and len(stock_prices) > 1000:
                        print(f"[BSE EOD] ✅ Found valid data for {date_display}")
                        print(f"[BSE EOD] Parsed {len(stock_prices)} stocks from {len(df)} rows")
                        
                        # Update cache and return immediately
                        BSE_STOCK_PRICES = stock_prices
                        
                        return stock_prices
                    else:
                        print(f"[BSE EOD] Data incomplete for {date_display} ({len(stock_prices)} stocks), trying previous day...")
                        continue
                else:
                    print(f"[BSE EOD] Unexpected CSV format for {date_display}, trying previous day...")
                    continue
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # File doesn't exist - likely holiday, try next day
                    print(f"[BSE EOD] No file for {date_display} (404) - trying previous day...")
                    continue
                else:
                    print(f"[BSE EOD] HTTP {e.response.status_code} for {date_display}, trying previous day...")
                    continue
            except Exception as e:
                print(f"[BSE EOD] Error downloading for {date_display}: {e}")
                continue
        
        # If we reach here, no valid data found
        print("[BSE EOD] ❌ Could not find valid trading day data after checking 15 days")
        return None
        
    except ImportError as e:
        print(f"[BSE EOD] ⚠️ Required package not installed: {e}")
        print("[BSE EOD] Install with: pip install requests pandas")
        return None
    except Exception as e:
        print(f"[BSE EOD] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_stock_price(symbol):
    """Get stock price from cache by symbol"""
    if symbol and BSE_STOCK_PRICES:
        symbol_upper = symbol.upper()
        if symbol_upper in BSE_STOCK_PRICES:
            return BSE_STOCK_PRICES[symbol_upper]
    return None


def get_stock_prices_cache():
    """Get the entire stock prices cache dictionary"""
    return BSE_STOCK_PRICES


def refresh_stock_prices():
    """Refresh BSE stock prices dictionary (non-blocking)"""
    def refresh_in_background():
        result = download_bse_eod_data()
        if result:
            print(f"[BSE EOD] ✅ Successfully refreshed cache with {len(BSE_STOCK_PRICES)} stocks")
        else:
            print("[BSE EOD] ⚠️ Failed to refresh cache")
    
    thread = threading.Thread(target=refresh_in_background, daemon=True)
    thread.start()
    return len(BSE_STOCK_PRICES)


def initialize_bse_stock_prices():
    """Initialize BSE stock prices cache on server startup (non-blocking)"""
    def fetch_in_background():
        print("[BSE EOD] Initializing stock prices cache on server startup...")
        result = download_bse_eod_data()
        if result:
            print(f"[BSE EOD] ✅ Successfully initialized cache with {len(BSE_STOCK_PRICES)} stocks")
        else:
            print("[BSE EOD] ⚠️ Failed to initialize cache on startup")
            print("[BSE EOD] 💡 You can manually refresh using the refresh endpoint later")
    
    # Start fetching in background thread so server can start immediately
    thread = threading.Thread(target=fetch_in_background, daemon=True)
    thread.start()

