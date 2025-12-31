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

PORT = 8000
BSE_API_URL = 'https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&strCat=Company+Update&strPrevDate=20251231&strScrip=&strSearch=P&strToDate=20251231&strType=C&subcategory=Award+of+Order+%2F+Receipt+of+Order'

# Try to import KiteConnect, but make it optional
try:
    from kiteconnect import KiteConnect
    KITE_AVAILABLE = True
except ImportError:
    KITE_AVAILABLE = False
    print("⚠️  KiteConnect not installed. Install with: pip install kiteconnect")

def load_kite_config():
    """Load Kite API configuration"""
    config_path = 'kite_config.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {
        "api_key": "",
        "api_secret": "",
        "access_token": "",
        "request_token": "",
        "redirect_url": "",
        "postback_url": ""
    }

def save_kite_config(config):
    """Save Kite API configuration"""
    with open('kite_config.json', 'w') as f:
        json.dump(config, f, indent=4)

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
            req = urllib.request.Request(BSE_API_URL)
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
            
            # Try multiple methods to get stock price
            
            # Method 1: Try BSE StockTrading API (has WAP which is close to current price)
            try:
                price_url = f'https://api.bseindia.com/BseIndiaAPI/api/StockTrading/w?scripcode={scrip_code}&flag=&seriesid='
                req = urllib.request.Request(price_url)
                req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
                req.add_header('Referer', 'https://www.bseindia.com/')
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    if data and 'WAP' in data:
                        # Return WAP (Weighted Average Price) as current price
                        result = {
                            'price': float(data.get('WAP', 0)),
                            'source': 'BSE_WAP',
                            'data': data
                        }
                        response_data = json.dumps(result).encode()
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Content-Length', str(len(response_data)))
                        self.end_headers()
                        self.wfile.write(response_data)
                        return
            except:
                pass
            
            # Method 2: Try Yahoo Finance if symbol is available
            if symbol:
                try:
                    # BSE stocks on Yahoo Finance use .BO suffix
                    yahoo_symbol = f"{symbol.upper()}.BO"
                    yahoo_url = f'https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1d&range=1d'
                    req = urllib.request.Request(yahoo_url)
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read().decode())
                        if data and 'chart' in data and 'result' in data['chart']:
                            result_data = data['chart']['result'][0]
                            if 'meta' in result_data and 'regularMarketPrice' in result_data['meta']:
                                price = result_data['meta']['regularMarketPrice']
                                result = {
                                    'price': price,
                                    'source': 'Yahoo_Finance',
                                    'currency': result_data['meta'].get('currency', 'INR')
                                }
                                response_data = json.dumps(result).encode()
                                self.send_response(200)
                                self.send_header('Content-Type', 'application/json')
                                self.send_header('Access-Control-Allow-Origin', '*')
                                self.send_header('Content-Length', str(len(response_data)))
                                self.end_headers()
                                self.wfile.write(response_data)
                                return
                except:
                    pass
            
            # If all methods fail, return error
            error_data = json.dumps({'error': 'Price not available', 'scrip_code': scrip_code}).encode()
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
            login_url = kite.login_url()
            
            self.send_json_response({
                'login_url': login_url,
                'message': 'Redirect user to this URL for authentication'
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
            
            if not request_token:
                self.send_error(400, 'Missing request_token')
                return
            
            config = load_kite_config()
            if not config.get('api_key') or not config.get('api_secret'):
                self.send_error(400, 'API credentials not configured')
                return
            
            if not KITE_AVAILABLE:
                self.send_error(500, 'KiteConnect library not installed')
                return
            
            kite = KiteConnect(api_key=config['api_key'])
            data = kite.generate_session(request_token, api_secret=config['api_secret'])
            
            # Save access token
            config['access_token'] = data['access_token']
            config['request_token'] = request_token
            save_kite_config(config)
            
            # Redirect to success page
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Kite Authentication Success</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Authentication Successful!</h1>
                <p>You can now close this window and return to the dashboard.</p>
                <script>setTimeout(() => window.close(), 3000);</script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        except Exception as e:
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
            
            self.send_json_response({
                'configured': is_configured,
                'authenticated': is_authenticated,
                'kite_available': KITE_AVAILABLE
            })
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def kite_place_order(self):
        """Place order via Kite API"""
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
            
            # Map BSE symbol to NSE (Kite uses NSE)
            # Note: You may need to adjust symbol mapping based on your needs
            trading_symbol = order_data.get('symbol', '').upper()
            exchange = order_data.get('exchange', 'NSE')  # Default to NSE
            quantity = int(order_data.get('quantity', 1))
            
            # Place order
            order_id = kite.place_order(
                tradingsymbol=trading_symbol,
                exchange=exchange,
                transaction_type=order_data.get('transaction_type', 'BUY'),
                quantity=quantity,
                order_type=order_data.get('order_type', 'MARKET'),
                product=order_data.get('product', 'CNC')  # CNC for delivery
            )
            
            self.send_json_response({
                'success': True,
                'order_id': order_id,
                'message': f'Order placed successfully for {quantity} shares of {trading_symbol}'
            })
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def kite_update_config(self):
        """Update Kite configuration"""
        try:
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
    
    server = HTTPServer(("", PORT), ProxyHandler)
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

