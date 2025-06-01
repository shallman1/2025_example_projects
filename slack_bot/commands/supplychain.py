# commands/supplychain.py

import asyncio
import os
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from analysis.subdomain_finder import run_subdomain_finder
from datetime import datetime
from config import DNSDB_API_KEY

def register_supplychain_command(app: AsyncApp):

    @app.command("/supplychain")
    async def handle_supplychain_command(ack, say, command, client):
        await ack()

        channel_id = command['channel_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the domains from the command text
        domains_text = command['text'].strip()

        if not domains_text:
            await say("Please provide at least one domain. Usage: /supplychain <domain1,domain2,...>")
            return

        domains = [domain.strip() for domain in domains_text.split(',') if domain.strip()]

        try:
            # Run the subdomain finder and get subdomains as data
            _, subdomains = await run_subdomain_finder(domains, DNSDB_API_KEY)

            # Read the brands.csv file
            brands = read_brands_csv()

            # Search for brands terms in the subdomains
            results = find_brands_in_subdomains(subdomains, brands)

            # Build the report
            report = generate_supplychain_report(results)

            # Send the report back to the user
            if report:
                await say(report)
            else:
                await say("No matching brands terms found in the subdomains.")

        except Exception as e:
            await say(f"An error occurred during supply chain analysis: {str(e)}")

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

    def read_brands_csv():
        filepath = os.path.join(os.path.dirname(__file__), 'brands.csv')
        brands = set()
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                brand = line.strip()
                if brand:
                    brands.add(brand.lower())
        return brands

    def find_brands_in_subdomains(subdomains, brands):
        # subdomains is a dict of fqdn -> time_last
        # brands is a set of brand terms
        brand_matches = {}

        for fqdn, time_last in subdomains.items():
            lower_fqdn = fqdn.lower()
            for brand in brands:
                if brand.lower() in lower_fqdn:
                    # Check if this is the first time we find this brand
                    if brand not in brand_matches:
                        brand_matches[brand] = {'fqdn': fqdn, 'time_last': time_last}
                    else:
                        # Compare time_last to keep the most recent
                        if time_last > brand_matches[brand]['time_last']:
                            brand_matches[brand] = {'fqdn': fqdn, 'time_last': time_last}

        return brand_matches  # Returns a dict of brand -> {'fqdn': fqdn, 'time_last': time_last}

    def generate_supplychain_report(results):
        if not results:
            return None
        report_lines = ["*Supply Chain Analysis Results:*"]
        for brand, data in results.items():
            fqdn = data['fqdn']
            time_last = data['time_last']
            # Convert time_last to a human-readable date
            date_str = datetime.utcfromtimestamp(time_last).strftime('%Y-%m-%d %H:%M:%S UTC')
            report_lines.append(f"- *{brand}* found in `{fqdn}` (last seen: {date_str})")
        return '\n'.join(report_lines)
