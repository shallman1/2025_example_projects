# commands/dns_history.py

import asyncio
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from utils.validation_utils import is_valid_ip, is_valid_domain
from analysis.dns_history import run_dns_history_analysis
from config import DNSDB_API_KEY

def register_dns_history_command(app: AsyncApp):

    @app.command("/dns_history")
    async def handle_dns_history_command(ack, say, command, client):
        await ack()

        channel_id = command['channel_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the domains/IPs from the command text
        input_text = command['text'].strip()

        if not input_text:
            await say("Please provide at least one domain or IP. Usage: /dns_history <domain_or_ip1>,<domain_or_ip2>,...")
            return

        # Split the input text into items
        items = [item.strip() for item in input_text.split(',') if item.strip()]

        # Separate domains and IPs
        domains = []
        ips = []
        invalid_items = []

        for item in items:
            if is_valid_ip(item):
                ips.append(item)
            elif is_valid_domain(item):
                domains.append(item.rstrip('.'))  # Remove trailing dot if present
            else:
                invalid_items.append(item)

        if invalid_items:
            await say(f"Invalid input(s): {', '.join(invalid_items)}. Please provide valid domains or IP addresses.")
            return

        try:
            # Run the DNS history analysis
            overlapping_data = await run_dns_history_analysis(domains, ips, DNSDB_API_KEY)

            # Build a report of the overlapping data
            report = generate_dns_history_report(overlapping_data)

            # Send the report back to the user
            if report:
                await say(report)
            else:
                await say("No overlapping data found among the provided domains and IPs.")

        except Exception as e:
            await say(f"An error occurred during DNS history analysis: {str(e)}")

    def generate_dns_history_report(overlapping_data):
        report_lines = []

        overlapping_ips = overlapping_data['overlapping_ips']
        overlapping_hostnames = overlapping_data['overlapping_hostnames']

        if overlapping_ips:
            report_lines.append("*Overlapping IP addresses found:*")
            for ip, items in overlapping_ips.items():
                items_str = ', '.join(items)
                report_lines.append(f"- {ip} shared among: {items_str}")
        else:
            report_lines.append("No overlapping IP addresses found.")

        if overlapping_hostnames:
            report_lines.append("\n*Overlapping hostnames found:*")
            for hostname, items in overlapping_hostnames.items():
                items_str = ', '.join(items)
                report_lines.append(f"- {hostname} shared among: {items_str}")
        else:
            report_lines.append("No overlapping hostnames found.")

        return '\n'.join(report_lines)

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
