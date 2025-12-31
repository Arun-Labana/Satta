# Deploying to Render

This guide will help you deploy the BSE Announcements Dashboard to Render.

## Prerequisites

1. GitHub account with the repository pushed
2. Render account (sign up at https://render.com - free tier available)

## Step 1: Prepare Repository

✅ Already done! The repository is ready with:
- `render.yaml` - Render configuration
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification
- Updated code to use environment variables

## Step 2: Create Render Account

1. Go to https://render.com
2. Sign up with your GitHub account (recommended)
3. Connect your GitHub account

## Step 3: Create New Web Service

1. **Click "New +"** → **"Web Service"**
2. **Connect your repository:**
   - Select "Arun-Labana/Satta" repository
   - Click "Connect"

3. **Configure the service:**
   - **Name**: `bse-announcements-dashboard` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python proxy_server.py`
   - **Plan**: Free (or choose paid for better performance)

4. **Environment Variables** (Optional - for Kite API):
   ```
   KITE_API_KEY=your_api_key_here
   KITE_API_SECRET=your_api_secret_here
   KITE_REDIRECT_URL=https://your-app-name.onrender.com/kite/callback
   KITE_POSTBACK_URL=https://your-app-name.onrender.com/kite/postback
   ```
   ⚠️ **Important**: Add these AFTER deployment to get your app URL first!

5. **Click "Create Web Service"**

## Step 4: Wait for Deployment

- Render will automatically:
  - Clone your repository
  - Install dependencies
  - Start your application
- First deployment takes 5-10 minutes
- You'll get a URL like: `https://bse-announcements-dashboard.onrender.com`

## Step 5: Configure Kite API (If Using)

**Your Render URL**: https://satta-3avv.onrender.com

1. **Update Kite App Settings:**
   - Go to https://developers.kite.trade/
   - Edit your app
   - Set:
     - **Redirect URL**: `https://satta-3avv.onrender.com/kite/callback`
     - **Postback URL**: `https://satta-3avv.onrender.com/kite/postback`
   - Save changes

2. **Add Environment Variables in Render:**
   - Go to your Render service dashboard: https://dashboard.render.com
   - Select your service: `bse-announcements-dashboard`
   - Click "Environment" tab
   - Add these variables:
     ```
     KITE_API_KEY=your_api_key
     KITE_API_SECRET=your_api_secret
     KITE_REDIRECT_URL=https://satta-3avv.onrender.com/kite/callback
     KITE_POSTBACK_URL=https://satta-3avv.onrender.com/kite/postback
     ```
   - Click "Save Changes"
   - Render will automatically redeploy (takes 2-3 minutes)

## Step 6: Access Your Dashboard

- Your dashboard will be available at: `https://your-app-name.onrender.com`
- Share this URL with others!

## Features on Render

✅ **Automatic HTTPS** - No need for ngrok!
✅ **Fixed URL** - Your URL never changes
✅ **Auto-deploy** - Pushes to GitHub automatically deploy
✅ **Free Tier Available** - Perfect for development/testing

## Free Tier Limitations

- **Spins down after 15 minutes of inactivity** - First request may be slow
- **512 MB RAM** - Should be sufficient for this app
- **Limited CPU** - Fine for this use case

## Upgrading (Optional)

For production use, consider:
- **Starter Plan ($7/month)** - Always on, no spin-down
- **Standard Plan ($25/month)** - Better performance

## Troubleshooting

### App won't start
- Check build logs in Render dashboard
- Verify `requirements.txt` is correct
- Check Python version matches `runtime.txt`

### Kite API not working
- Verify environment variables are set correctly
- Check URLs match your Render app URL
- Ensure HTTPS URLs are used (Render provides this automatically)

### Slow first request
- This is normal on free tier (spins down after inactivity)
- Consider upgrading to Starter plan for always-on

## Updating Your App

Simply push to GitHub:
```bash
git add .
git commit -m "Your changes"
git push
```

Render will automatically detect and deploy the changes!

