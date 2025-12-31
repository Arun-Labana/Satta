# Kite API Integration Setup Guide

This guide will help you set up Zerodha Kite API integration for automated trading.

## Prerequisites

1. **Zerodha Account**: You need an active Zerodha trading account
2. **Kite Connect API Access**: Register at [Kite Developer Portal](https://developers.kite.trade/)

## Step 1: Install KiteConnect Library

```bash
pip install kiteconnect
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

## Step 2: Set up HTTPS Tunnel (Required for Postback URL)

**⚠️ IMPORTANT**: Kite requires HTTPS URLs. For local development, you need a tunnel service.

### Quick Setup with ngrok:

1. **Install ngrok:**
   ```bash
   brew install ngrok
   # Or download from https://ngrok.com/download
   ```

2. **Start your server:**
   ```bash
   python3 proxy_server.py
   ```

3. **In a new terminal, start ngrok:**
   ```bash
   ngrok http 8000
   ```

4. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

5. **Use these URLs:**
   - Redirect URL: `https://abc123.ngrok.io/kite/callback`
   - Postback URL: `https://abc123.ngrok.io/kite/postback`

**Note:** Free ngrok URLs change each restart. See `ngrok_setup.md` for alternatives and details.

## Step 3: Get API Credentials

1. Go to [Kite Developer Portal](https://developers.kite.trade/)
2. Sign in with your Zerodha credentials
3. Create a new app
4. **IMPORTANT**: Set both URLs in your app settings (use HTTPS URLs from ngrok):
   - **Redirect URL**: `https://your-ngrok-url.ngrok.io/kite/callback`
   - **Postback URL**: `https://your-ngrok-url.ngrok.io/kite/postback`
5. Note down your:
   - **API Key**
   - **API Secret**

## Step 3: Configure API Credentials

1. Click "⚙️ Kite Config" button in the dashboard
2. Enter your API Key and API Secret
3. Click "Save Configuration"

## Step 4: Authenticate

1. Click "🔐 Login to Kite" button
2. A popup window will open with Zerodha login page
3. Login with your Zerodha credentials
4. Authorize the app
5. You'll be redirected back and authenticated

## Step 5: Place Orders

Once authenticated, you can:
- Click "🛒 Buy with ₹3000" button on any announcement
- The system will automatically calculate how many shares you can buy
- Confirm the order to place it via Kite API

## Important Notes

### Symbol Mapping
- **BSE vs NSE**: The dashboard shows BSE announcements, but Kite API primarily uses NSE symbols
- You may need to map BSE symbols to NSE symbols manually
- Some stocks trade on both exchanges with different symbols

### Order Details
- **Order Type**: MARKET (executes immediately at current price)
- **Product**: CNC (Cash and Carry - delivery)
- **Exchange**: NSE (default)
- **Investment**: ₹3000 per order

### Security
- API credentials are stored locally in `kite_config.json`
- Access tokens expire daily - you'll need to re-authenticate
- Never share your API credentials

### Limitations
- Free Kite API has rate limits
- Access tokens expire daily
- Some features may require paid Kite Connect subscription

## Troubleshooting

### "KiteConnect library not installed"
- Run: `pip install kiteconnect`

### "Not authenticated"
- Click "Login to Kite" and complete authentication

### "Order failed"
- Check if symbol exists on NSE
- Verify you have sufficient funds
- Ensure market is open (9:15 AM - 3:30 PM IST)

### Symbol not found
- BSE symbols may not match NSE symbols
- You may need to manually map symbols or use NSE symbol lookup

## API Endpoints

- `GET /api/kite/login` - Get login URL
- `GET /api/kite/status` - Check authentication status
- `GET /kite/callback` - OAuth callback handler
- `POST /api/kite/order` - Place order
- `POST /api/kite/config` - Update configuration

## Support

For Kite API issues, refer to:
- [Kite Connect Documentation](https://kite.trade/docs/connect/v3/)
- [Kite Developer Portal](https://developers.kite.trade/)

