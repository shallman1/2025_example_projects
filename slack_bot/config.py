# config.py

import os
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

# Iris Investigate API credentials
IRIS_API_KEY = config.get('iris', 'api_key')
IRIS_USER = config.get('iris', 'api_username')

# Slack tokens
SLACK_BOT_TOKEN = config.get('slack', 'bot_token')
SLACK_APP_TOKEN = config.get('slack', 'app_token')

# DNSDB API Key
DNSDB_API_KEY = config.get('dnsdb', 'api_key')

#freeimage
FREEIMAGE_API_KEY = config.get('freeimage', 'api_key')

# Screenshot configuration
SCREENSHOT_OUTPUT_DIR = config.get('screenshot', 'output_dir', fallback='screenshots')
