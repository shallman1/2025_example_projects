# commands/mx_security.py

import asyncio
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from utils.validation_utils import is_valid_domain
from utils.api_utils import query_dnsdb_rrset_name
from models.dnsdb_models import DnsdbRecord
from datetime import datetime
import re
import aiohttp
import time

def register_mx_security_command(app: AsyncApp):

    @app.command("/mx_security")
    async def handle_mx_security_command(ack, say, command, client):
        await ack()

        channel_id = command['channel_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the domain from the command text
        domain = command['text'].strip()

        if not domain:
            await say("Please provide a domain. Usage: /mx_security <domain>")
            return

        if not is_valid_domain(domain):
            await say(f"The domain '{domain}' is not valid. Please provide a valid domain.")
            return

        try:
            # Query DNSDB for SPF, DKIM, and DMARC records
            records = await get_mx_security_records(domain)

            if not records:
                await say(f"No SPF, DKIM, or DMARC records found for domain '{domain}'.")
                return

            # Format the records for presentation
            message = format_mx_security_records(records, domain)

            # Send the formatted message back to the user
            await say(message)

        except Exception as e:
            await say(f"An error occurred during MX security analysis: {str(e)}")

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

    async def get_mx_security_records(domain):
        """
        Queries DNSDB for SPF, DKIM, and DMARC TXT records of the given domain.
        Returns a dictionary of records.
        """
        from config import DNSDB_API_KEY

        # Compute time_last_after (e.g., 30 days before current time)
        current_time = int(time.time())
        thirty_days = 30 * 24 * 60 * 60
        time_last_after = current_time - thirty_days

        async with aiohttp.ClientSession() as session:
            tasks = []

            # Prepare the queries for SPF, DKIM, and DMARC
            dmarc_query = f'_dmarc.{domain}'
            dkim_query = f'*._domainkey.{domain}'
            spf_query = f'{domain}'

            # Query for DMARC records
            tasks.append(query_dnsdb_rrset_name(
                session,
                DNSDB_API_KEY,
                dmarc_query,
                rrtype='TXT',
                limit=5000,
                time_last_after=time_last_after
            ))

            # Query for DKIM records
            tasks.append(query_dnsdb_rrset_name(
                session,
                DNSDB_API_KEY,
                dkim_query,
                rrtype='TXT',
                limit=5000,
                time_last_after=time_last_after
            ))

            # Query for SPF records (TXT records at root domain)
            tasks.append(query_dnsdb_rrset_name(
                session,
                DNSDB_API_KEY,
                spf_query,
                rrtype='TXT',
                limit=5000,
                time_last_after=time_last_after
            ))

            # Run the queries concurrently
            results = await asyncio.gather(*tasks)

            # Combine and return the records
            combined_records = {
                'dmarc': results[0],
                'dkim': results[1],
                'spf': results[2]
            }

            return combined_records

    def format_mx_security_records(records, domain):
        """
        Formats the SPF, DKIM, and DMARC records into a Markdown message.
        """
        lines = [f"*SPF, DKIM, and DMARC Records for {domain}:*"]

        # Format SPF Records
        spf_records = records.get('spf', [])
        spf_lines = format_spf_records(spf_records, domain)
        if spf_lines:
            lines.append("\n*SPF Records:*")
            lines.extend(spf_lines)
        else:
            lines.append("\n*SPF Records:* None found.")

        # Format DMARC Records
        dmarc_records = records.get('dmarc', [])
        dmarc_lines = format_dmarc_dkim_records(dmarc_records, 'DMARC')
        if dmarc_lines:
            lines.append("\n*DMARC Records:*")
            lines.extend(dmarc_lines)
        else:
            lines.append("\n*DMARC Records:* None found.")

        # Format DKIM Records
        dkim_records = records.get('dkim', [])
        dkim_lines = format_dmarc_dkim_records(dkim_records, 'DKIM')
        if dkim_lines:
            lines.append("\n*DKIM Records:*")
            lines.extend(dkim_lines)
        else:
            lines.append("\n*DKIM Records:* None found.")

        return '\n'.join(lines)

    def format_spf_records(spf_records, domain):
        """
        Formats SPF records from TXT records at the root domain.
        """
        lines = []
        # Group records by rrname
        records_by_rrname = {}
        for record in spf_records:
            rrname = record.rrname.rstrip('.')
            records_by_rrname.setdefault(rrname, []).append(record)

        for rrname, rr_records in records_by_rrname.items():
            for record in rr_records:
                for rdata in record.rdata:
                    if 'v=spf1' in rdata.lower():
                        # It's an SPF record
                        lines.append(f"\n*Record Name:* `{rrname}`")
                        # Format the timeline
                        time_first = datetime.utcfromtimestamp(record.time_first).strftime('%Y-%m-%d %H:%M:%S UTC') if record.time_first else 'Unknown'
                        time_last = datetime.utcfromtimestamp(record.time_last).strftime('%Y-%m-%d %H:%M:%S UTC') if record.time_last else 'Unknown'
                        lines.append(f"- *First Seen:* {time_first}")
                        lines.append(f"  *Last Seen:* {time_last}")
                        # Parse the SPF record
                        parsed_params = parse_spf_record(rdata)
                        # Format the parameters
                        params_lines = []
                        for param in parsed_params:
                            params_lines.append(f"    - {param}")
                        lines.append("  *Record Details:*")
                        lines.extend(params_lines)
        return lines

    def parse_spf_record(txt_record):
        """
        Parses an SPF TXT record string into a list of mechanisms and modifiers.
        """
        # Remove quotes if present
        txt_record = txt_record.strip('"')
        # Split the record into terms
        terms = re.split(r'\s+', txt_record)
        return terms

    def format_dmarc_dkim_records(records, record_type):
        """
        Formats the DMARC or DKIM records into a list of strings.
        """
        lines = []
        # Group records by rrname
        records_by_rrname = {}
        for record in records:
            rrname = record.rrname.rstrip('.')
            records_by_rrname.setdefault(rrname, []).append(record)

        for rrname, rr_records in records_by_rrname.items():
            lines.append(f"\n*Record Name:* `{rrname}`")

            for record in rr_records:
                # Format the timeline
                time_first = datetime.utcfromtimestamp(record.time_first).strftime('%Y-%m-%d %H:%M:%S UTC') if record.time_first else 'Unknown'
                time_last = datetime.utcfromtimestamp(record.time_last).strftime('%Y-%m-%d %H:%M:%S UTC') if record.time_last else 'Unknown'
                lines.append(f"- *First Seen:* {time_first}")
                lines.append(f"  *Last Seen:* {time_last}")

                for rdata in record.rdata:
                    # Parse the TXT record
                    parsed_params = parse_txt_record(rdata)

                    # Truncate keys if necessary
                    if 'p' in parsed_params:
                        parsed_params['p'] = parsed_params['p'][:32] + '...' if len(parsed_params['p']) > 35 else parsed_params['p']

                    # Format the parameters
                    params_lines = []
                    for key, value in parsed_params.items():
                        params_lines.append(f"    - *{key}*: {value}")
                    lines.append("  *Record Details:*")
                    lines.extend(params_lines)
        return lines

    def parse_txt_record(txt_record):
        """
        Parses a TXT record string into a dictionary of parameters.
        """
        # Remove quotes if present
        txt_record = txt_record.strip('"')
        # Split the record into parameters
        params = re.split(r';\s*', txt_record)
        parsed_params = {}
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)
                parsed_params[key.strip()] = value.strip()
            else:
                parsed_params[param.strip()] = ''
        return parsed_params
