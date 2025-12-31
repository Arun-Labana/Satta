#!/usr/bin/env python3
"""
Configuration management module for Kite API settings.
Handles loading and saving configuration from file and environment variables.
"""

import json
import os


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

