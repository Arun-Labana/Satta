#!/usr/bin/env python3
"""
Kite API client module.
Handles KiteConnect authentication, orders, and instrument downloads.
"""

import os
import json
import csv
import io

# Try to import KiteConnect, but make it optional
try:
    from kiteconnect import KiteConnect
    KITE_AVAILABLE = True
except ImportError:
    KITE_AVAILABLE = False
    print("⚠️  KiteConnect not installed. Install with: pip install kiteconnect")

# Global KiteConnect instance cache (to avoid recreating on every request)
KITE_INSTANCE = None
KITE_INSTANCE_API_KEY = None
KITE_INSTANCE_ACCESS_TOKEN = None

from config import load_kite_config, save_kite_config


def get_kite_instance():
    """Get or create KiteConnect instance (cached for performance)"""
    global KITE_INSTANCE, KITE_INSTANCE_API_KEY, KITE_INSTANCE_ACCESS_TOKEN
    
    if not KITE_AVAILABLE:
        return None
    
    config = load_kite_config()
    api_key = config.get('api_key', '')
    access_token = config.get('access_token', '')
    
    if not api_key:
        return None
    
    # Create new instance if:
    # 1. No instance exists
    # 2. API key changed
    # 3. Access token changed (token refreshed)
    if (KITE_INSTANCE is None or 
        KITE_INSTANCE_API_KEY != api_key or 
        KITE_INSTANCE_ACCESS_TOKEN != access_token):
        
        KITE_INSTANCE = KiteConnect(api_key=api_key)
        if access_token:
            KITE_INSTANCE.set_access_token(access_token)
        
        KITE_INSTANCE_API_KEY = api_key
        KITE_INSTANCE_ACCESS_TOKEN = access_token
        
        print(f"[Kite] Created new KiteConnect instance (API key: {api_key[:10]}..., Token: {access_token[:20] if access_token else 'None'}...)")
    
    return KITE_INSTANCE


def invalidate_kite_instance():
    """Invalidate cached Kite instance (call after token refresh)"""
    global KITE_INSTANCE, KITE_INSTANCE_API_KEY, KITE_INSTANCE_ACCESS_TOKEN
    KITE_INSTANCE = None
    KITE_INSTANCE_API_KEY = None
    KITE_INSTANCE_ACCESS_TOKEN = None


def get_login_url(redirect_url=None):
    """Generate Kite login URL"""
    if not KITE_AVAILABLE:
        raise ValueError('KiteConnect library not installed')
    
    config = load_kite_config()
    if not config.get('api_key'):
        raise ValueError('API key not configured')
    
    kite = KiteConnect(api_key=config['api_key'])
    return kite.login_url()


def handle_oauth_callback(request_token):
    """Handle Kite OAuth callback and generate access token"""
    if not KITE_AVAILABLE:
        raise ValueError('KiteConnect library not installed')
    
    config = load_kite_config()
    if not config.get('api_key') or not config.get('api_secret'):
        raise ValueError('API credentials not configured')
    
    kite = KiteConnect(api_key=config['api_key'])
    data = kite.generate_session(request_token, api_secret=config['api_secret'])
    
    # Save access token
    config['access_token'] = data['access_token']
    config['request_token'] = request_token
    
    # Invalidate Kite instance cache so new token is used immediately
    invalidate_kite_instance()
    
    # Save to file
    try:
        save_kite_config(config)
        print(f"[Kite Callback] Config saved to kite_config.json successfully")
    except Exception as e:
        print(f"[Kite Callback] WARNING: Failed to save config to file: {e}")
    
    return data


def get_status():
    """Get Kite authentication status"""
    config = load_kite_config()
    is_configured = bool(config.get('api_key') and config.get('api_secret'))
    is_authenticated = bool(config.get('access_token'))
    has_env_vars = bool(os.environ.get('KITE_API_KEY') and os.environ.get('KITE_API_SECRET'))
    
    return {
        'configured': is_configured,
        'authenticated': is_authenticated,
        'kite_available': KITE_AVAILABLE,
        'has_env_vars': has_env_vars,
        'redirect_url': config.get('redirect_url', ''),
        'postback_url': config.get('postback_url', '')
    }


def place_order(order_data):
    """Place order via Kite API"""
    if not KITE_AVAILABLE:
        raise ValueError('KiteConnect library not installed')
    
    kite = get_kite_instance()
    if not kite:
        config = load_kite_config()
        if not config.get('access_token'):
            raise ValueError('Not authenticated. Please login first.')
        if not config.get('api_key'):
            raise ValueError('Kite API key not configured')
        # Fallback: create new instance if cache failed
        kite = KiteConnect(api_key=config['api_key'])
        kite.set_access_token(config['access_token'])
    
    trading_symbol = order_data.get('tradingsymbol', '').upper().strip()
    if not trading_symbol:
        raise ValueError('Trading symbol is required')
    
    quantity = int(order_data.get('quantity', 1))
    if quantity <= 0:
        raise ValueError('Quantity must be greater than 0')
    
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
    
    return {
        'order_id': order_id,
        'message': f'Order placed successfully for {quantity} shares of {trading_symbol} on {exchange}'
    }


def download_instruments(exchange=None, equity_only=False):
    """Download all instruments as CSV content"""
    if not KITE_AVAILABLE:
        raise ValueError('KiteConnect library not installed')
    
    config = load_kite_config()
    if not config.get('access_token'):
        raise ValueError('Not authenticated. Please login first.')
    
    kite = KiteConnect(api_key=config['api_key'])
    kite.set_access_token(config['access_token'])
    
    # Fetch instruments
    instruments = kite.instruments(exchange=exchange) if exchange else kite.instruments()
    
    # Filter for equity only if requested
    if equity_only:
        instruments = [inst for inst in instruments if inst.get('instrument_type') == 'EQ']
    
    if not instruments:
        raise ValueError('No instruments found')
    
    # Convert to CSV
    output = io.StringIO()
    fieldnames = ['tradingsymbol', 'name', 'exchange', 'instrument_type', 'segment', 'strike', 'tick_size', 'lot_size', 'expiry']
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    
    writer.writeheader()
    for inst in instruments:
        writer.writerow(inst)
    
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename
    exchange_suffix = f"_{exchange}" if exchange else ""
    equity_suffix = "_equity_only" if equity_only else ""
    filename = f"kite_instruments{exchange_suffix}{equity_suffix}.csv"
    
    return csv_content, filename


def update_config(new_config):
    """Update Kite configuration"""
    # Check if using environment variables (production)
    if os.environ.get('KITE_API_KEY'):
        raise ValueError('Configuration is managed via environment variables in Render. Update them in Render dashboard instead.')
    
    config = load_kite_config()
    config.update(new_config)
    save_kite_config(config)

