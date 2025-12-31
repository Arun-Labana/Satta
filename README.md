# BSE Announcements Dashboard with Kite API Integration

A real-time dashboard that monitors BSE India announcements, displays stock prices, calculates investment opportunities, and allows automated trading via Zerodha Kite API.

## Features

- 🔄 **Auto-refresh**: Fetches announcements every 2 seconds
- 🔔 **Sound notifications**: Plays a 6-beep notification sound when new announcements are detected
- 📊 **Statistics**: Shows total announcements and new announcements count
- 💰 **Amount Detection**: Automatically identifies announcements with rupee amounts
- 📈 **Stock Prices**: Fetches and displays current stock prices
- 🧮 **Investment Calculator**: Calculates how many shares can be bought with ₹3000
- 🛒 **Kite API Integration**: Place buy orders directly from the dashboard
- 🎨 **Modern UI**: Beautiful, responsive design
- ⏸️ **Start/Stop control**: Pause and resume monitoring
- 🔕 **Sound toggle**: Enable/disable sound notifications
- 🔍 **Filter**: Show only announcements with amounts

## Installation

### Quick Start

```bash
# Clone or navigate to the project directory
cd satta

# Run the start script (creates venv and installs dependencies)
./start.sh
```

### Manual Installation

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install ngrok (for HTTPS tunnel - required for Kite API):**
   ```bash
   brew install ngrok
   ```

4. **Start the server:**
   ```bash
   python3 proxy_server.py
   ```

## How to Use

### Starting the Dashboard

1. **Start the proxy server:**
   ```bash
   python3 proxy_server.py
   # Or use: ./start.sh
   ```

2. **Open in browser:**
   - Navigate to `http://localhost:8000`

### Using the Dashboard

1. **Monitor Announcements:**
   - Click "Start Monitoring" to begin fetching announcements
   - The dashboard automatically refreshes every 2 seconds
   - New announcements trigger a 6-beep sound notification

2. **View Stock Information:**
   - Stock prices are automatically fetched and displayed
   - Investment calculator shows how many shares you can buy with ₹3000

3. **Filter Announcements:**
   - Toggle "Show Only With Amounts" to filter announcements with rupee values

### Setting up Kite API (Optional - for Trading)

1. **Set up HTTPS tunnel:**
   ```bash
   # In a new terminal
   ngrok http 8000
   # Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
   ```

2. **Configure Kite API:**
   - Click "⚙️ Kite Config" in the dashboard
   - Enter your API Key and Secret from [Kite Developer Portal](https://developers.kite.trade/)
   - Add URLs:
     - Redirect URL: `https://your-ngrok-url.ngrok.io/kite/callback`
     - Postback URL: `https://your-ngrok-url.ngrok.io/kite/postback`
   - Save configuration

3. **Authenticate:**
   - Click "🔐 Login to Kite"
   - Complete authentication in the popup window

4. **Place Orders:**
   - Click "🛒 Buy with ₹3000" on any announcement
   - Confirm the order to execute via Kite API

See `KITE_SETUP.md` and `ngrok_setup.md` for detailed instructions.

## Troubleshooting

### "Failed to fetch" Error

This is a CORS (Cross-Origin Resource Sharing) issue. The browser blocks API requests from local files. Solutions:

1. **Use a local server** (recommended) - See "Option 1" above
2. **Use a CORS browser extension** - Install a CORS extension for your browser
3. **The code includes a CORS proxy** - It should automatically try a proxy if direct fetch fails

### Sound Not Playing

- Make sure your system volume is up
- Check that "Sound Notifications" toggle is enabled
- Click "Test Sound" to verify audio works
- Some browsers require user interaction before playing sounds

## Files

- `index.html` - Main HTML structure
- `styles.css` - Styling and animations
- `script.js` - JavaScript logic for API polling and notifications
- `README.md` - This file

## API Details

The dashboard fetches data from:
```
https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
```

With parameters:
- Category: Company Update
- Subcategory: Award of Order / Receipt of Order
- Date range: 2025-12-31
- Search: P

## Browser Compatibility

- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

Note: Sound notifications use Web Audio API, which is supported in all modern browsers.

## Customization

You can customize the polling interval by changing `POLL_INTERVAL` in `script.js`:
```javascript
const POLL_INTERVAL = 2000; // Change to desired milliseconds
```

You can also modify the API URL and parameters in the `API_URL` constant in `script.js`.

