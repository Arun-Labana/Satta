# Render Deployment URL

## Your Live Dashboard

🌐 **Production URL**: https://satta-3avv.onrender.com

## Kite API Configuration

Use these URLs for Kite API setup:

### In Kite Developer Portal (https://developers.kite.trade/):
- **Redirect URL**: `https://satta-3avv.onrender.com/kite/callback`
- **Postback URL**: `https://satta-3avv.onrender.com/kite/postback`

### In Render Dashboard (Environment Variables):
Add these environment variables in your Render service settings:

```
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here
KITE_REDIRECT_URL=https://satta-3avv.onrender.com/kite/callback
KITE_POSTBACK_URL=https://satta-3avv.onrender.com/kite/postback
```

## Testing Your Dashboard

1. **Visit**: https://satta-3avv.onrender.com
2. **Click "Start Monitoring"** to begin fetching announcements
3. **Test Sound**: Click "🔊 Test Sound" to verify notifications
4. **Configure Kite** (optional): Click "⚙️ Kite Config" to set up trading

## Features Available

✅ Real-time BSE announcements monitoring
✅ Stock price fetching
✅ Investment calculator (₹3000)
✅ Sound notifications
✅ Kite API integration (after configuration)

## Notes

- **Free Tier**: App may spin down after 15 minutes of inactivity
- **First Request**: May be slow (cold start on free tier)
- **HTTPS**: Automatically provided by Render - no ngrok needed!

