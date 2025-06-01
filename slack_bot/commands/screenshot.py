# commands/screenshot.py

import asyncio
import io
import os
from urllib.parse import urlparse
import aiohttp
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
import logging
import boto3
from datetime import datetime

from config import SCREENSHOT_OUTPUT_DIR  # We'll add this to config
from utils.validation_utils import is_valid_url

# Import the screenshot functionality
from playwright.async_api import async_playwright
import cloudscraper
from PIL import Image
import random

# List of user agents (from your script)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def register_screenshot_command(app: AsyncApp):

    @app.command("/screenshot")
    async def handle_screenshot_command(ack, say, command, client, logger):
        await ack()

        channel_id = command['channel_id']
        user_id = command['user_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the URL from the command text
        text = command['text'].strip()

        if not text:
            await say("Please provide a URL. Usage: /screenshot <url> [browser_type]")
            return

        # Parse arguments
        args = text.split()
        url = args[0]
        browser_type = args[1] if len(args) > 1 else "chromium"

        # Validate URL
        if not is_valid_url(url):
            await say(f"Invalid URL: {url}. Please provide a valid URL.")
            return

        # Validate browser type
        valid_browsers = ["chromium", "firefox", "webkit"]
        if browser_type not in valid_browsers:
            await say(f"Invalid browser type: {browser_type}. Valid options are: {', '.join(valid_browsers)}")
            return

        try:
            # Send initial message
            await say(f"Taking a screenshot of {url} using {browser_type}. This may take a few moments...")

            # Take the screenshot
            screenshot_bytes = await take_screenshot(url, browser_type, logger)

            # Create a temporary file to upload to Slack
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            domain = urlparse(url).netloc
            filename = f"{domain}_{timestamp}.jpg"
            
            # Create screenshots directory if it doesn't exist
            os.makedirs(SCREENSHOT_OUTPUT_DIR, exist_ok=True)
            filepath = os.path.join(SCREENSHOT_OUTPUT_DIR, filename)
            
            # Save the screenshot to a file
            with open(filepath, 'wb') as f:
                screenshot_bytes.seek(0)
                f.write(screenshot_bytes.read())
            
            try:
                # Try to upload to S3 first
                try:
                    # Reset the file pointer to the beginning before uploading to S3
                    screenshot_bytes.seek(0)
                    image_url = await upload_image_to_s3(screenshot_bytes, url)
                    
                    # Send the screenshot to Slack using S3 URL
                    await say(
                        blocks=[
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"Screenshot of *{url}* using *{browser_type}*"
                                }
                            },
                            {
                                "type": "image",
                                "image_url": image_url,
                                "alt_text": f"Screenshot of {url}"
                            }
                        ]
                    )
                    
                    # Clean up the temporary file after successful S3 upload and Slack message
                    os.remove(filepath)
                except Exception as s3_error:
                    logger.warning(f"S3 upload failed, falling back to direct Slack upload: {s3_error}")
                    
                    # If S3 upload fails, upload directly to Slack using the saved file
                    upload_response = await client.files_upload_v2(
                        channel=channel_id,
                        file=filepath,
                        filename=filename,
                        title=f"Screenshot of {url}"
                    )
                    
                    # Clean up the temporary file after direct upload
                    os.remove(filepath)
            except Exception as upload_error:
                # Make sure we clean up the file even if both upload methods fail
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                logger.error(f"Error uploading screenshot: {upload_error}")
                await say(f"Error uploading screenshot: {str(upload_error)}")

        except Exception as e:
            logger.error(f"Error in /screenshot command: {e}")
            await say(f"An error occurred while taking the screenshot: {str(e)}")

    # Helper functions follow the same pattern as timeline.py
    async def ensure_bot_in_channel(client, channel_id, say):
        try:
            await client.chat_postMessage(channel=channel_id, text="Processing your request. This may take a few moments...")
            return True
        except SlackApiError as e:
            if e.response['error'] == 'not_in_channel':
                if await join_channel(client, channel_id):
                    await client.chat_postMessage(channel=channel_id, text="I've joined the channel. Processing your request. This may take a few moments...")
                    return True
                else:
                    await say("I couldn't join the channel. Please add me to this channel and try again.")
                    return False
            else:
                await say(f"An error occurred: {str(e)}")
                return False

    async def join_channel(client, channel_id):
        try:
            await client.conversations_join(channel=channel_id)
            return True
        except SlackApiError as e:
            print(f"Error joining channel: {e}")
            return False

    # Core screenshot functionality adapted from your script
    async def take_screenshot(url, browser_type="chromium", logger=None):
        """
        Take a screenshot of the specified URL using Playwright with Cloudflare bypass.
        Returns the screenshot as bytes.
        """
        # Add https:// prefix if not present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Select a random user agent
        user_agent = random.choice(USER_AGENTS)
        if logger:
            logger.info(f"Using user agent: {user_agent}")

        # Configure Cloudscraper
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True,
                'mobile': False
            },
            delay=10,
        )

        # Set custom headers
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        try:
            # Send an initial request with Cloudscraper
            if logger:
                logger.info("Initializing connection with Cloudscraper...")
            response = scraper.get(url, headers=headers)
            cookies = scraper.cookies.get_dict()

            # Convert cookies to Playwright format
            playwright_cookies = [
                {"name": name, "value": value, "domain": urlparse(url).netloc, "path": "/"}
                for name, value in cookies.items()
            ]

            async with async_playwright() as p:
                # Setup browser launch options
                browser_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--disable-extensions',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                ]

                browser_options = {
                    'args': browser_args,
                    'headless': True,  # Run headless in production
                }

                # Launch browser based on user selection
                if browser_type.lower() == "firefox":
                    browser = await p.firefox.launch(**browser_options)
                elif browser_type.lower() == "webkit":
                    browser = await p.webkit.launch(**browser_options)
                else:  # Default to chromium
                    browser = await p.chromium.launch(**browser_options)

                # Create browser context with advanced options
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=user_agent,
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation'],
                    java_script_enabled=True,
                    is_mobile=False,
                    has_touch=False,
                    color_scheme='light',
                )

                # Add additional headers
                await context.set_extra_http_headers(headers)

                # Set cookies from Cloudscraper
                if playwright_cookies:
                    await context.add_cookies(playwright_cookies)

                # Create new page
                page = await context.new_page()

                # Add anti-detection script
                await page.add_init_script("""
                    () => {
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => false,
                        });
                        window.chrome = { runtime: {} };
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                originalQuery(parameters)
                        );
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                        });
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en'],
                        });
                    }
                """)

                # Navigate to the URL
                if logger:
                    logger.info("Navigating to the website...")
                try:
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                except Exception as e:
                    if logger:
                        logger.warning(f"Navigation error: {e}")
                        logger.info("Continuing anyway as the page might have partially loaded...")

                # Simulate human behavior
                await simulate_human_behavior(page)

                # Take screenshot
                if logger:
                    logger.info("Taking screenshot...")
                screenshot_bytes = await page.screenshot(full_page=True)

                # Convert PNG to JPG
                image = Image.open(io.BytesIO(screenshot_bytes))
                rgb_image = image.convert('RGB')
                
                # Save to BytesIO instead of file
                buf = io.BytesIO()
                rgb_image.save(buf, 'JPEG', quality=95)
                buf.seek(0)

                # Close browser
                await browser.close()

                return buf

        except Exception as e:
            if logger:
                logger.error(f"Error taking screenshot: {e}")
            raise

    async def simulate_human_behavior(page):
        """Simulate human-like behavior to bypass bot detection."""
        # Random initial wait
        await page.wait_for_timeout(random.randint(1000, 3000))
        
        # Scroll down gradually with random speed and pauses
        for i in range(3):
            # Random scroll amount
            scroll_amount = random.randint(300, 800)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            # Random pause between scrolls
            await page.wait_for_timeout(random.randint(500, 2000))
        
        # Scroll back up a bit (humans do this)
        await page.evaluate("window.scrollBy(0, -300)")
        await page.wait_for_timeout(random.randint(500, 1500))
        
        # Move mouse to simulate cursor movement
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

    async def upload_image_to_s3(image_bytes, url):
        """
        Upload the image to AWS S3 and return the public URL.
        Following the same pattern as timeline.py
        """
        s3_bucket_name = 'slackrepo'
        domain = urlparse(url).netloc
        s3_key = f'screenshots/{domain}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.jpg'

        s3_client = boto3.client('s3')

        def upload():
            s3_client.upload_fileobj(
                Fileobj=image_bytes,
                Bucket=s3_bucket_name,
                Key=s3_key,
                ExtraArgs={'ContentType': 'image/jpeg', 'ACL': 'public-read'}
            )

        # Run the upload in a thread to avoid blocking the event loop
        await asyncio.to_thread(upload)

        # Generate the public URL
        image_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_key}'

        return image_url
