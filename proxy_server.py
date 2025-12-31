#!/usr/bin/env python3
"""
Backend proxy server to fetch BSE API data and bypass CORS/403 issues.
This server acts as a proxy between your frontend and the BSE API.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import webbrowser
import os
from datetime import datetime, timedelta

# Get PORT from environment variable (Render provides this) or default to 8000
PORT = int(os.environ.get('PORT', 8000))

def get_bse_announcements_url():
    """Generate BSE announcements URL with today's date"""
    today = datetime.now().strftime('%Y%m%d')
    return f'https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&strCat=Company+Update&strPrevDate={today}&strScrip=&strSearch=P&strToDate={today}&strType=C&subcategory=Award+of+Order+%2F+Receipt+of+Order'

# Global dictionary for BSE stock prices (symbol -> closing_price)
BSE_STOCK_PRICES = {}

# Try to import KiteConnect, but make it optional
try:
    from kiteconnect import KiteConnect
    KITE_AVAILABLE = True
except ImportError:
    KITE_AVAILABLE = False
    print("⚠️  KiteConnect not installed. Install with: pip install kiteconnect")

def load_kite_config():
    """Load Kite API configuration from file or environment variables"""
    # Start with environment variables (for Render/production)
    config = {
        "api_key": os.environ.get('KITE_API_KEY', ''),
        "api_secret": os.environ.get('KITE_API_SECRET', ''),
        "access_token": os.environ.get('KITE_ACCESS_TOKEN', ''),
        "request_token": os.environ.get('KITE_REQUEST_TOKEN', ''),
        "redirect_url": os.environ.get('KITE_REDIRECT_URL', ''),
        "postback_url": os.environ.get('KITE_POSTBACK_URL', '')
    }
    
    # Always try to load from file to get access_token (even if env vars exist)
    # The access_token is dynamic and won't be in env vars
    if os.path.exists('kite_config.json'):
        try:
            with open('kite_config.json', 'r') as f:
                file_config = json.load(f)
                # Merge file config, but prioritize env vars for credentials
                # This allows access_token from file to be loaded even when using env vars
                if not config.get('api_key'):
                    config['api_key'] = file_config.get('api_key', '')
                if not config.get('api_secret'):
                    config['api_secret'] = file_config.get('api_secret', '')
                # Always use access_token from file if it exists (it's dynamic)
                if file_config.get('access_token'):
                    config['access_token'] = file_config.get('access_token')
                if file_config.get('request_token'):
                    config['request_token'] = file_config.get('request_token')
                # Use file config for URLs if not in env vars
                if not config.get('redirect_url'):
                    config['redirect_url'] = file_config.get('redirect_url', '')
                if not config.get('postback_url'):
                    config['postback_url'] = file_config.get('postback_url', '')
        except Exception as e:
            print(f"[Config] Error loading kite_config.json: {e}")
    
    return config

def save_kite_config(config):
    """Save Kite API configuration"""
    with open('kite_config.json', 'w') as f:
        json.dump(config, f, indent=4)

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
        from datetime import date as date_class
        
        today = datetime.now()
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

def initialize_bse_stock_prices():
    """Initialize BSE stock prices cache on server startup (non-blocking)"""
    import threading
    
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

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            # Serve the HTML file
            self.serve_file('index.html', 'text/html')
        elif self.path.startswith('/api/announcements'):
            # Proxy API request
            self.proxy_api_request()
        elif self.path.startswith('/api/stock-price'):
            # Fetch stock price
            self.proxy_stock_price()
        elif self.path.startswith('/api/kite/login'):
            # Kite login URL
            self.kite_login()
        elif self.path.startswith('/kite/callback'):
            # Kite OAuth callback
            self.kite_callback()
        elif self.path.startswith('/kite/postback'):
            # Kite postback URL (for webhooks)
            self.kite_postback()
        elif self.path.startswith('/api/kite/status'):
            # Check Kite authentication status
            self.kite_status()
        elif self.path.endswith('.css'):
            self.serve_file(self.path[1:], 'text/css')
        elif self.path.endswith('.js'):
            self.serve_file(self.path[1:], 'application/javascript')
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path.startswith('/api/kite/order'):
            # Place order via Kite API
            self.kite_place_order()
        elif self.path.startswith('/api/kite/config'):
            # Update Kite config
            self.kite_update_config()
        else:
            self.send_error(404)
    
    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)
    
    def proxy_api_request(self):
        try:
            # Create request with proper headers to mimic browser
            req = urllib.request.Request(get_bse_announcements_url())
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
            req.add_header('Accept', 'application/json, text/plain, */*')
            req.add_header('Referer', 'https://www.bseindia.com/')
            req.add_header('Origin', 'https://www.bseindia.com')
            req.add_header('sec-ch-ua', '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"')
            req.add_header('sec-ch-ua-mobile', '?0')
            req.add_header('sec-ch-ua-platform', '"macOS"')
            req.add_header('DNT', '1')
            
            # Make the request
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_data = json.dumps({'error': f'HTTP {e.code}: {e.reason}'}).encode()
            self.wfile.write(error_data)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_data = json.dumps({'error': str(e)}).encode()
            self.wfile.write(error_data)
    
    def proxy_stock_price(self):
        try:
            # Extract scrip code and symbol from query parameters
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            scrip_code = params.get('scrip', [None])[0]
            symbol = params.get('symbol', [None])[0]
            
            if not scrip_code:
                raise ValueError('Scrip code is required')
            
            # Only use BSE_STOCK_PRICES dictionary (no fallback APIs)
            if symbol and BSE_STOCK_PRICES:
                symbol_upper = symbol.upper()
                if symbol_upper in BSE_STOCK_PRICES:
                    price = BSE_STOCK_PRICES[symbol_upper]
                    result = {
                        'price': price,
                        'source': 'BSE_EOD_Cache',
                        'symbol': symbol_upper
                    }
                    response_data = json.dumps(result).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Content-Length', str(len(response_data)))
                    self.end_headers()
                    self.wfile.write(response_data)
                    return
            
            # If not found in dictionary, return error
            # TODO: Uncomment fallback methods below if needed in future
            
            # # Method 2: Try BSE StockTrading API (has WAP which is close to current price)
            # try:
            #     price_url = f'https://api.bseindia.com/BseIndiaAPI/api/StockTrading/w?scripcode={scrip_code}&flag=&seriesid='
            #     req = urllib.request.Request(price_url)
            #     req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            #     req.add_header('Referer', 'https://www.bseindia.com/')
            #     
            #     with urllib.request.urlopen(req, timeout=5) as response:
            #         data = json.loads(response.read().decode())
            #         if data and 'WAP' in data:
            #             # Return WAP (Weighted Average Price) as current price
            #             result = {
            #                 'price': float(data.get('WAP', 0)),
            #                 'source': 'BSE_WAP',
            #                 'data': data
            #             }
            #             response_data = json.dumps(result).encode()
            #             self.send_response(200)
            #             self.send_header('Content-Type', 'application/json')
            #             self.send_header('Access-Control-Allow-Origin', '*')
            #             self.send_header('Content-Length', str(len(response_data)))
            #             self.end_headers()
            #             self.wfile.write(response_data)
            #             return
            # except:
            #     pass
            # 
            # # Method 3: Try Yahoo Finance if symbol is available
            # if symbol:
            #     try:
            #         # BSE stocks on Yahoo Finance use .BO suffix
            #         yahoo_symbol = f"{symbol.upper()}.BO"
            #         yahoo_url = f'https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1d&range=1d'
            #         req = urllib.request.Request(yahoo_url)
            #         req.add_header('User-Agent', 'Mozilla/5.0')
            #         
            #         with urllib.request.urlopen(req, timeout=5) as response:
            #             data = json.loads(response.read().decode())
            #             if data and 'chart' in data and 'result' in data['chart']:
            #                 result_data = data['chart']['result'][0]
            #                 if 'meta' in result_data and 'regularMarketPrice' in result_data['meta']:
            #                     price = result_data['meta']['regularMarketPrice']
            #                     result = {
            #                         'price': price,
            #                         'source': 'Yahoo_Finance',
            #                         'currency': result_data['meta'].get('currency', 'INR')
            #                     }
            #                     response_data = json.dumps(result).encode()
            #                     self.send_response(200)
            #                     self.send_header('Content-Type', 'application/json')
            #                     self.send_header('Access-Control-Allow-Origin', '*')
            #                     self.send_header('Content-Length', str(len(response_data)))
            #                     self.end_headers()
            #                     self.wfile.write(response_data)
            #                     return
            #     except:
            #         pass
            
            error_data = json.dumps({
                'error': 'Price not available in cache',
                'scrip_code': scrip_code,
                'symbol': symbol,
                'message': 'Stock price not found in BSE EOD cache. Please refresh the cache.'
            }).encode()
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(error_data)))
            self.end_headers()
            self.wfile.write(error_data)
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_data = json.dumps({'error': str(e)}).encode()
            self.wfile.write(error_data)
    
    def kite_login(self):
        """Generate Kite login URL"""
        try:
            config = load_kite_config()
            if not config.get('api_key'):
                self.send_json_response({'error': 'API key not configured'}, 400)
                return
            
            if not KITE_AVAILABLE:
                self.send_json_response({'error': 'KiteConnect library not installed'}, 500)
                return
            
            kite = KiteConnect(api_key=config['api_key'])
            
            # Use redirect_url from config if available, otherwise construct from request
            redirect_url = config.get('redirect_url')
            if not redirect_url:
                # Try to get from request headers (for Render/production)
                host = self.headers.get('Host', '')
                if host:
                    redirect_url = f'https://{host}/kite/callback'
                else:
                    redirect_url = 'http://localhost:8000/kite/callback'
            
            login_url = kite.login_url()
            
            self.send_json_response({
                'login_url': login_url,
                'message': 'Redirect user to this URL for authentication',
                'redirect_url': redirect_url
            })
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def kite_callback(self):
        """Handle Kite OAuth callback"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            request_token = params.get('request_token', [None])[0]
            
            print(f"[Kite Callback] Received callback, request_token present: {request_token is not None}")
            
            if not request_token:
                self.send_error(400, 'Missing request_token')
                return
            
            config = load_kite_config()
            if not config.get('api_key') or not config.get('api_secret'):
                print("[Kite Callback] ERROR: API credentials not configured")
                self.send_error(400, 'API credentials not configured')
                return
            
            if not KITE_AVAILABLE:
                self.send_error(500, 'KiteConnect library not installed')
                return
            
            kite = KiteConnect(api_key=config['api_key'])
            data = kite.generate_session(request_token, api_secret=config['api_secret'])
            
            print(f"[Kite Callback] Session generated, access_token received: {bool(data.get('access_token'))}")
            
            # Save access token
            config['access_token'] = data['access_token']
            config['request_token'] = request_token
            
            # Save to file (this is critical for persistence)
            try:
                save_kite_config(config)
                print(f"[Kite Callback] Config saved to kite_config.json successfully")
            except Exception as e:
                print(f"[Kite Callback] WARNING: Failed to save config to file: {e}")
                # If file save fails, token is only in memory for this request
                # On Render, file system might be read-only, so we need another solution
                pass
            
            # Redirect to success page
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Kite Authentication Success</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Authentication Successful!</h1>
                <p>You can now close this window and return to the dashboard.</p>
                <script>
                    console.log('[Kite Callback] Page loaded, checking window.opener...');
                    console.log('[Kite Callback] window.opener exists:', !!window.opener);
                    // Notify parent window about successful authentication
                    if (window.opener) {
                        console.log('[Kite Callback] Sending postMessage to parent window...');
                        window.opener.postMessage({ type: 'kite_auth_success' }, '*');
                        console.log('[Kite Callback] postMessage sent');
                    } else {
                        console.error('[Kite Callback] window.opener is null! Cannot send message to parent.');
                    }
                    setTimeout(() => {
                        console.log('[Kite Callback] Closing window...');
                        window.close();
                    }, 2000);
                </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        except Exception as e:
            print(f"[Kite Callback] Error: {e}")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Kite Authentication Error</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Authentication Failed</h1>
                <p>{str(e)}</p>
            </body>
            </html>
            """
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(error_html.encode())
    
    def kite_postback(self):
        """Handle Kite postback URL (for webhooks/order updates)"""
        try:
            # Read POST data if available
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode()) if post_data else {}
                print(f"[Kite Postback] Received: {data}")
            
            # Return success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        except Exception as e:
            print(f"[Kite Postback] Error: {e}")
            self.send_response(200)  # Always return 200 to Kite
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
    
    def kite_status(self):
        """Check Kite authentication status"""
        try:
            config = load_kite_config()
            is_configured = bool(config.get('api_key') and config.get('api_secret'))
            is_authenticated = bool(config.get('access_token'))
            has_env_vars = bool(os.environ.get('KITE_API_KEY') and os.environ.get('KITE_API_SECRET'))
            
            print(f"[Kite Status] Request received")
            print(f"[Kite Status] configured: {is_configured}, authenticated: {is_authenticated}")
            print(f"[Kite Status] has_env_vars: {has_env_vars}")
            print(f"[Kite Status] access_token present: {bool(config.get('access_token'))}")
            print(f"[Kite Status] access_token length: {len(config.get('access_token', ''))}")
            print(f"[Kite Status] File exists: {os.path.exists('kite_config.json')}")
            
            self.send_json_response({
                'configured': is_configured,
                'authenticated': is_authenticated,
                'kite_available': KITE_AVAILABLE,
                'has_env_vars': has_env_vars,
                'redirect_url': config.get('redirect_url', ''),
                'postback_url': config.get('postback_url', '')
            })
        except Exception as e:
            print(f"[Kite Status] Error: {e}")
            self.send_json_response({'error': str(e)}, 500)
    
    def kite_place_order(self):
        """Place order via Kite API with instrument validation"""
        try:
            if not KITE_AVAILABLE:
                self.send_json_response({'error': 'KiteConnect library not installed'}, 500)
                return
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data.decode())
            
            config = load_kite_config()
            if not config.get('access_token'):
                self.send_json_response({'error': 'Not authenticated. Please login first.'}, 401)
                return
            
            kite = KiteConnect(api_key=config['api_key'])
            kite.set_access_token(config['access_token'])
            
            trading_symbol = order_data.get('tradingsymbol', '').upper().strip()
            if not trading_symbol:
                self.send_json_response({'error': 'Trading symbol is required'}, 400)
                return
            
            quantity = int(order_data.get('quantity', 1))
            if quantity <= 0:
                self.send_json_response({'error': 'Quantity must be greater than 0'}, 400)
                return
            
            # Get exchange, default to NSE (Kite primarily uses NSE)
            exchange = order_data.get('exchange', 'NSE').upper()
            if exchange not in ['NSE', 'BSE']:
                exchange = 'NSE'
            
            print(f"[Kite Order] Placing order: {trading_symbol} on {exchange}, qty: {quantity}")
            
            # Place order directly - let Kite API handle validation (faster, no extra API calls)
            # Validity: DAY (valid for entire trading day) or IOC (Immediate or Cancel)
            # For MARKET orders, IOC is recommended; for LIMIT orders, DAY is common
            order_type = order_data.get('order_type', 'MARKET')
            default_validity = 'IOC' if order_type == 'MARKET' else 'DAY'
            validity = order_data.get('validity', default_validity)
            
            order_id = kite.place_order(
                tradingsymbol=trading_symbol,
                exchange=exchange,
                transaction_type=order_data.get('transaction_type', 'BUY'),
                quantity=quantity,
                order_type=order_type,
                product=order_data.get('product', 'CNC'),  # CNC for delivery
                variety=order_data.get('variety', 'regular'),  # regular, amo, co, bo, iceberg
                validity=validity  # DAY or IOC - required parameter
            )
            
            self.send_json_response({
                'success': True,
                'order_id': order_id,
                'message': f'Order placed successfully for {quantity} shares of {trading_symbol} on {exchange}'
            })
        except Exception as e:
            instruments = kite.instruments()
            error_msg = str(e) + " length of instruments is " + str(len(instruments))
            print(f"[Kite Order] Error: {error_msg}")
            # Provide more helpful error messages
            if 'instrument' in error_msg.lower() or 'expired' in error_msg.lower() or 'does not exist' in error_msg.lower():
                error_msg = (
                    f"Instrument error: {error_msg}\n\n"
                    f"This usually means:\n"
                    f"- The trading symbol '{order_data.get('tradingsymbol', '')}' doesn't exist on the specified exchange\n"
                    f"- The instrument has expired (for F&O contracts)\n"
                    f"- The symbol format is incorrect\n\n"
                    f"Please verify the symbol exists on Kite and try again. lenght is '{len(instruments)}'"
                )
            self.send_json_response({'error': error_msg}, 500)
    
    def kite_update_config(self):
        """Update Kite configuration"""
        try:
            # Check if using environment variables (production)
            if os.environ.get('KITE_API_KEY'):
                self.send_json_response({
                    'success': False,
                    'message': 'Configuration is managed via environment variables in Render. Update them in Render dashboard instead.',
                    'has_env_vars': True
                })
                return
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            new_config = json.loads(post_data.decode())
            
            config = load_kite_config()
            config.update(new_config)
            save_kite_config(config)
            
            self.send_json_response({'success': True, 'message': 'Configuration updated'})
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def send_json_response(self, data, status=200):
        """Helper to send JSON response"""
        response_data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)
    
    def log_message(self, format, *args):
        # Custom logging
        print(f"[{self.address_string()}] {format % args}")

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Initialize BSE stock prices cache on startup
    initialize_bse_stock_prices()
    
    # Determine if running on Render (has PORT env var and RENDER env)
    is_render = os.environ.get('RENDER') == 'true' or (os.environ.get('PORT') and not os.environ.get('PORT') == '8000')
    host = '0.0.0.0' if is_render else 'localhost'
    
    server = HTTPServer((host, PORT), ProxyHandler)
    
    if is_render:
        print(f"🚀 Server running on Render at port {PORT}")
        print(f"📂 Serving directory: {os.getcwd()}")
        print(f"🔗 API proxy endpoint: /api/announcements")
    else:
        print(f"🚀 Proxy server running at http://localhost:{PORT}")
        print(f"📂 Serving directory: {os.getcwd()}")
        print(f"🔗 API proxy endpoint: http://localhost:{PORT}/api/announcements")
        print("\nPress Ctrl+C to stop the server\n")
        
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")

if __name__ == "__main__":
    main()

