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
from urllib.parse import urlparse, parse_qs

# Import modular components
from config import load_kite_config, save_kite_config
from bse_client import (
    get_bse_announcements_url,
    get_stock_price,
    get_stock_prices_cache,
    refresh_stock_prices as refresh_bse_prices,
    initialize_bse_stock_prices
)
from kite_client import (
    get_login_url,
    handle_oauth_callback,
    get_status as get_kite_status,
    place_order as kite_place_order_func,
    download_instruments as kite_download_instruments_func,
    update_config as kite_update_config_func
)

# Get PORT from environment variable (Render provides this) or default to 8000
PORT = int(os.environ.get('PORT', 8000))


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
        elif self.path.startswith('/api/refresh-prices'):
            # Refresh BSE stock prices dictionary
            self.refresh_stock_prices()
        elif self.path.startswith('/api/kite/instruments'):
            # Download instruments as CSV
            self.kite_download_instruments()
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
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            scrip_code = params.get('scrip', [None])[0]
            symbol = params.get('symbol', [None])[0]
            
            if not scrip_code:
                raise ValueError('Scrip code is required')
            
            # Use BSE stock prices cache
            if symbol:
                price = get_stock_price(symbol)
                if price:
                    result = {
                        'price': price,
                        'source': 'BSE_EOD_Cache',
                        'symbol': symbol.upper()
                    }
                    self.send_json_response(result)
                    return
            
            # If not found in dictionary, return error
            error_data = {
                'error': 'Price not available in cache',
                'scrip_code': scrip_code,
                'symbol': symbol,
                'message': 'Stock price not found in BSE EOD cache. Please refresh the cache.'
            }
            self.send_json_response(error_data, 404)
            
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def refresh_stock_prices(self):
        """Refresh BSE stock prices dictionary"""
        try:
            print("[BSE EOD] Manual refresh requested")
            
            # Refresh in background and get current count
            current_count = refresh_bse_prices()
            
            # Return immediately with current status
            self.send_json_response({
                'success': True,
                'message': 'Stock prices refresh started in background',
                'current_count': current_count,
                'status': 'Refreshing...'
            })
        except Exception as e:
            print(f"[BSE EOD] Error refreshing prices: {e}")
            self.send_json_response({'error': str(e)}, 500)
    
    def kite_login(self):
        """Generate Kite login URL"""
        try:
            config = load_kite_config()
            if not config.get('api_key'):
                self.send_json_response({'error': 'API key not configured'}, 400)
                return
            
            # Use redirect_url from config if available, otherwise construct from request
            redirect_url = config.get('redirect_url')
            if not redirect_url:
                # Try to get from request headers (for Render/production)
                host = self.headers.get('Host', '')
                if host:
                    redirect_url = f'https://{host}/kite/callback'
                else:
                    redirect_url = 'http://localhost:8000/kite/callback'
            
            login_url = get_login_url(redirect_url)
            
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
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            request_token = params.get('request_token', [None])[0]
            
            print(f"[Kite Callback] Received callback, request_token present: {request_token is not None}")
            
            if not request_token:
                self.send_error(400, 'Missing request_token')
                return
            
            # Handle OAuth callback
            data = handle_oauth_callback(request_token)
            
            print(f"[Kite Callback] Session generated, access_token received: {bool(data.get('access_token'))}")
            
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
            status = get_kite_status()
            
            print(f"[Kite Status] Request received")
            print(f"[Kite Status] configured: {status['configured']}, authenticated: {status['authenticated']}")
            print(f"[Kite Status] has_env_vars: {status['has_env_vars']}")
            
            config = load_kite_config()
            print(f"[Kite Status] access_token present: {bool(config.get('access_token'))}")
            print(f"[Kite Status] access_token length: {len(config.get('access_token', ''))}")
            print(f"[Kite Status] File exists: {os.path.exists('kite_config.json')}")
            
            self.send_json_response(status)
        except Exception as e:
            print(f"[Kite Status] Error: {e}")
            self.send_json_response({'error': str(e)}, 500)
    
    def kite_place_order(self):
        """Place order via Kite API with instrument validation"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data.decode())
            
            result = kite_place_order_func(order_data)
            
            self.send_json_response({
                'success': True,
                **result
            })
        except Exception as e:
            error_msg = str(e)
            self.send_json_response({'error': error_msg}, 500)
    
    def kite_download_instruments(self):
        """Download all instruments as CSV file"""
        try:
            # Get exchange filter from query params
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            exchange = params.get('exchange', [None])[0]
            filter_eq = params.get('equity_only', ['false'])[0].lower() == 'true'
            
            csv_content, filename = kite_download_instruments_func(
                exchange=exchange,
                equity_only=filter_eq
            )
            
            # Send CSV file
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(csv_content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(csv_content.encode('utf-8'))
            
        except Exception as e:
            error_msg = str(e)
            print(f"[Kite Instruments] Error: {error_msg}")
            self.send_json_response({'error': error_msg}, 500)
    
    def kite_update_config(self):
        """Update Kite configuration"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            new_config = json.loads(post_data.decode())
            
            kite_update_config_func(new_config)
            
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
