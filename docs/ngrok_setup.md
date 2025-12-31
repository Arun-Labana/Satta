# Setting up HTTPS for Kite Postback URL (Local Development)

Kite API requires HTTPS URLs for the postback URL. Since we're running on localhost, we need to use a tunnel service like ngrok.

## Option 1: Using ngrok (Recommended)

### Step 1: Install ngrok

**macOS:**
```bash
brew install ngrok
```

**Or download from:** https://ngrok.com/download

### Step 2: Start your proxy server

```bash
python3 proxy_server.py
```

### Step 3: Start ngrok tunnel

In a new terminal:
```bash
ngrok http 8000
```

This will give you an HTTPS URL like: `https://abc123.ngrok.io`

### Step 4: Update Kite Configuration

1. Copy the HTTPS URL from ngrok (e.g., `https://abc123.ngrok.io`)
2. Update your URLs:
   - **Redirect URL**: `https://abc123.ngrok.io/kite/callback`
   - **Postback URL**: `https://abc123.ngrok.io/kite/postback`
3. Add these URLs in your Kite app settings
4. Update the configuration in the dashboard modal

### Step 5: Update Configuration

Click "⚙️ Kite Config" and update:
- Redirect URL: `https://your-ngrok-url.ngrok.io/kite/callback`
- Postback URL: `https://your-ngrok-url.ngrok.io/kite/postback`

**⚠️ Important:** Free ngrok URLs change every time you restart ngrok. You'll need to:
1. Update URLs in Kite app settings each time
2. Update URLs in dashboard config each time

**Options for Fixed URL:**
1. **ngrok Paid Plan** - Get a fixed domain (e.g., `https://yourname.ngrok.io`)
2. **Keep ngrok running** - Don't restart it, and the URL stays the same
3. **Use alternatives** - See options below

## Option 2: Using localtunnel (Free Alternative)

### Step 1: Install localtunnel

```bash
npm install -g localtunnel
```

### Step 2: Start tunnel

```bash
lt --port 8000
```

This will give you an HTTPS URL like: `https://random-name.loca.lt`

### Step 3: Update URLs

Use the provided HTTPS URL:
- **Redirect URL**: `https://random-name.loca.lt/kite/callback`
- **Postback URL**: `https://random-name.loca.lt/kite/postback`

## Option 3: Using Cloudflare Tunnel (Free)

```bash
# Install cloudflared
brew install cloudflared

# Start tunnel
cloudflared tunnel --url http://localhost:8000
```

## Important Notes

- **Free ngrok URLs expire**: Free ngrok URLs change on restart. Consider ngrok's paid plan for a fixed URL.
- **Security**: These tunnels expose your local server to the internet. Only use during development.
- **Production**: For production, deploy to a server with proper HTTPS (Let's Encrypt, etc.)

## Quick Start Script

Create a file `start_with_ngrok.sh`:

```bash
#!/bin/bash
# Start proxy server in background
python3 proxy_server.py &
SERVER_PID=$!

# Wait a moment
sleep 2

# Start ngrok
echo "Starting ngrok..."
ngrok http 8000

# Cleanup on exit
trap "kill $SERVER_PID" EXIT
```

Then run: `bash start_with_ngrok.sh`

