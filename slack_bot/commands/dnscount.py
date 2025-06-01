import asyncio
import io
import numpy as np
from datetime import datetime
import pandas as pd
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import boto3  # For AWS S3 integration
import aiohttp  # For async HTTP requests
from collections import defaultdict

from config import DNSDB_API_KEY
from utils.api_utils import query_dnsdb_rrset_name
from utils.validation_utils import is_valid_domain

def register_dnscount_command(app: AsyncApp):

    @app.command("/dnscount")
    async def handle_dnscount_command(ack, say, command, client, logger):
        await ack()

        channel_id = command['channel_id']
        user_id = command['user_id']

        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        text = command['text'].strip()
        if not text:
            await say("Please provide a domain. Usage: /dnscount <domain> or /dnscount -plot <domain>")
            return

        # Parse command arguments
        args = text.split()
        plot_mode = False
        
        if args[0] == '-plot':
            if len(args) < 2:
                await say("Please provide a domain. Usage: /dnscount -plot <domain>")
                return
            plot_mode = True
            domain = args[1]
        else:
            domain = args[0]

        try:
            if plot_mode:
                image_bytes = await generate_timeline_plot(domain)
                image_url = await upload_image_to_s3(image_bytes, f"timeline_{domain}")
                
                await say(
                    blocks=[
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"Here is the DNS record timeline for *{domain}*"}},
                        {"type": "image", "image_url": image_url, "alt_text": f"DNS Timeline for {domain}"}
                    ]
                )
            else:
                image_bytes = await generate_dnscount_image(domain)
                image_url = await upload_image_to_s3(image_bytes, domain)

                await say(
                    blocks=[
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"Here is the DNS count bar chart for *{domain}* and its subdomains."}},
                        {"type": "image", "image_url": image_url, "alt_text": f"DNS Count for {domain}"}
                    ]
                )

        except Exception as e:
            logger.error(f"Error in /dnscount command: {e}")
            await say(f"An error occurred during DNS analysis: {str(e)}")

    async def generate_timeline_plot(domain):
        async with aiohttp.ClientSession() as session:
            records = await get_dns_timeline_records(session, DNSDB_API_KEY, domain)

        if not records:
            raise ValueError(f"No DNS records found for {domain}")

        df = process_timeline_records(records)
        image_bytes = plot_dns_timeline(df, domain)
        return image_bytes

    async def get_dns_timeline_records(session, api_key, domain):
        if not is_valid_domain(domain):
            raise ValueError(f"Invalid domain: {domain}")

        wildcard_domain = f"*.{domain}"
        
        # Fetch records for both the main domain and its subdomains
        tasks = [
            query_dnsdb_rrset_name(session, api_key, domain, rrtype='ANY'),
            query_dnsdb_rrset_name(session, api_key, wildcard_domain, rrtype='ANY')
        ]
        
        results = await asyncio.gather(*tasks)
        records = [record for sublist in results for record in sublist if sublist]
        return records

    def process_timeline_records(records):
        """Process DNS records and create a DataFrame with timeline data focusing on top 10 domain/record type combinations"""
        # First, calculate total counts for each domain/rrtype combination
        total_counts = defaultdict(int)
        for record in records:
            if record.time_first and record.time_last:  # Skip records without timestamps
                key = (record.rrname, record.rrtype)
                total_counts[key] += record.count or 0

        # Get top 10 domain/rrtype combinations by total count
        top_combinations = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_combinations_set = {combo[0] for combo in top_combinations}  # Set of (rrname, rrtype) tuples

        data = []
        for record in records:
            # Skip records without timestamps or not in top 10 combinations
            if not record.time_first or not record.time_last:
                continue
                
            combo = (record.rrname, record.rrtype)
            if combo not in top_combinations_set:
                continue
                    
            # Add time_first entry
            data.append({
                'timestamp': datetime.fromtimestamp(record.time_first),
                'domain': record.rrname,
                'rrtype': record.rrtype,
                'count': record.count or 0
            })
            
            # Add time_last entry if different
            if record.time_last != record.time_first:
                data.append({
                    'timestamp': datetime.fromtimestamp(record.time_last),
                    'domain': record.rrname,
                    'rrtype': record.rrtype,
                    'count': record.count or 0
                })
        
        # Convert to DataFrame and sort by timestamp
        df = pd.DataFrame(data)
        if df.empty:
            raise ValueError("No valid timeline data found")
            
        df = df.sort_values('timestamp')
        
        # Calculate the time range
        time_range = (df['timestamp'].max() - df['timestamp'].min()).days
        
        # Determine the appropriate time bucket size
        if time_range <= 60:  # 2 months or less
            freq = 'D'  # Daily buckets
        elif time_range <= 365:  # 1 year or less
            freq = 'W'  # Weekly buckets
        else:
            freq = 'M'  # Monthly buckets
            
        # Resample the data based on the determined frequency
        df.set_index('timestamp', inplace=True)
        # Sum counts for each domain/rrtype combination within each time bucket
        df = df.groupby(['domain', 'rrtype', pd.Grouper(freq=freq)])['count'].sum().reset_index()
        
        return df

    def plot_dns_timeline(df, domain):
        """Create a line plot showing DNS record counts over time for top domains"""
        plt.figure(figsize=(12, 6))
        
        # Get unique domain and record type combinations
        domain_rrtype_pairs = df.groupby(['domain', 'rrtype'])['count'].sum().reset_index()
        domain_rrtype_pairs = domain_rrtype_pairs.sort_values('count', ascending=False)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(domain_rrtype_pairs)))
        
        # Plot a line for each unique domain and record type combination
        for (idx, row), color in zip(domain_rrtype_pairs.iterrows(), colors):
            mask = (df['domain'] == row['domain']) & (df['rrtype'] == row['rrtype'])
            
            # Truncate domain name if too long
            display_domain = row['domain'][:30] + '...' if len(row['domain']) > 30 else row['domain']
            label = f"{display_domain} ({row['rrtype']})"
            
            plt.plot(df[mask]['timestamp'], df[mask]['count'], 
                    label=label, color=color, marker='o')
        
        plt.title(f'Top 10 DNS Records Timeline for {domain} and Subdomains')
        plt.xlabel('Time')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        
        return buf

    async def ensure_bot_in_channel(client, channel_id, say):
        try:
            await client.chat_postMessage(channel=channel_id, text="Processing your request. This may take a few moments...")
            return True
        except SlackApiError as e:
            if e.response['error'] == 'not_in_channel':
                if await join_channel(client, channel_id):
                    await client.chat_postMessage(channel=channel_id, text="I've joined the channel. Processing your request...")
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

    async def generate_dnscount_image(domain):
        async with aiohttp.ClientSession() as session:
            records = await get_dns_records(session, DNSDB_API_KEY, domain)

        if not records:
            raise ValueError(f"No DNS records found for {domain} and its subdomains.")

        df = process_records(records)
        image_bytes = plot_dnscount_bar_chart(df, domain)
        return image_bytes

    async def get_dns_records(session, api_key, domain):
        if not is_valid_domain(domain):
            raise ValueError(f"Invalid domain: {domain}")

        wildcard_domain = f"*.{domain}"
        
        # Concurrently fetch records in chunks
        tasks = [
            query_dnsdb_rrset_name(session, api_key, wildcard_domain, rrtype='ANY', limit=5000, offset=i * 5000)
            for i in range(4)  # Adjust range based on desired concurrency
        ]
        
        # Gather all tasks concurrently
        results = await asyncio.gather(*tasks)
        # Flatten the list of lists into a single list of records
        records = [record for sublist in results for record in sublist if sublist]
        
        return records

    def process_records(records):
        """
        Aggregates DNSDB records by unique (rrname, rrtype) and sums their counts.
        """
        record_counts = defaultdict(int)

        # Aggregate counts by (rrname, rrtype) combination
        for record in records:
            count = record.count or 0  # Ensure count is not None
            rrtype = record.rrtype
            rrname = record.rrname

            # Generate a unique key for each (rrname, rrtype)
            identifier = (rrname, rrtype)

            # Sum counts for each unique identifier
            record_counts[identifier] += count

        # Convert to DataFrame, sort by count, and get the top 10 records
        data = [{'rrname': k[0], 'rrtype': k[1], 'count': v} for k, v in record_counts.items()]
        df = pd.DataFrame(data)
        df = df.sort_values(by='count', ascending=False).head(10)

        return df

    def plot_dnscount_bar_chart(df, domain):
        # Limit rrname to 25 characters
        df['rrname_short'] = df['rrname'].apply(lambda x: x[:25])

        # Create labels with record name and record type
        df['label'] = df['rrname_short'] + '\n' + df['rrtype'] + ' Record'

        x = np.arange(len(df))  # the label locations
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = plt.get_cmap('tab10').colors[:len(df)]

        bars = ax.bar(x, df['count'], color=colors)
        ax.set_xlabel('Record')
        ax.set_ylabel('Aggregated Count')
        ax.set_title(f'Top 10 Records by Aggregated Count for {domain} and Subdomains', fontsize=14)

        ax.set_xticks(x)
        ax.set_xticklabels(df['label'], rotation=45, ha='right')

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=600)
        plt.close(fig)
        buf.seek(0)

        return buf

    async def upload_image_to_s3(image_bytes, domain):
        s3_bucket_name = 'slackrepo'
        s3_key = f'dns_count/{domain}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.png'

        s3_client = boto3.client('s3')

        def upload():
            s3_client.upload_fileobj(
                Fileobj=image_bytes,
                Bucket=s3_bucket_name,
                Key=s3_key,
                ExtraArgs={'ContentType': 'image/png', 'ACL': 'public-read'}
            )

        await asyncio.to_thread(upload)
        image_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_key}'
        return image_url