# commands/timeline.py

import asyncio
import os
import io
import aiohttp
import numpy as np
from datetime import datetime
import pandas as pd
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
import logging

import boto3  # Added for AWS S3 integration
import asyncio  # Required for async operations

from config import DNSDB_API_KEY # Ensure AWS_S3_BUCKET_NAME is in your config
from utils.api_utils import query_dnsdb_rrset_name
from utils.validation_utils import is_valid_domain

def register_timeline_command(app: AsyncApp):

    @app.command("/timeline")
    async def handle_timeline_command(ack, say, command, client, logger):
        await ack()

        channel_id = command['channel_id']
        user_id = command['user_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the domain from the command text
        text = command['text'].strip()

        if not text:
            await say("Please provide a domain. Usage: /timeline <domain>")
            return

        domain = text

        try:
            # Run the timeline analysis and get the image
            image_bytes = await generate_timeline_image(domain)

            # Upload the image to AWS S3
            image_url = await upload_image_to_s3(image_bytes, domain)

            # Send a message to Slack with the image embedded
            await say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Here is the DNS timeline for *{domain}*."
                        }
                    },
                    {
                        "type": "image",
                        "image_url": image_url,
                        "alt_text": f"DNS Timeline for {domain}"
                    }
                ]
            )

        except Exception as e:
            logger.error(f"Error in /timeline command: {e}")
            await say(f"An error occurred during timeline generation: {str(e)}")

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

    async def generate_timeline_image(domain):
        async with aiohttp.ClientSession() as session:
            # Get DNS records
            records = await get_dns_records(session, DNSDB_API_KEY, domain)

        # Process records to identify unique events
        events = process_records(records)

        # Select up to 15 events, evenly distributed over the timeline
        events, has_more_events = select_events(events, max_events=15)

        # Plot the timeline and get image bytes
        image_bytes = plot_timeline(events, domain, has_more_events)

        return image_bytes

    async def get_dns_records(session, api_key, domain):
        """
        Retrieve A and AAAA DNS records for the given domain using DNSDB.
        """
        # Validate the domain
        if not is_valid_domain(domain):
            raise ValueError(f"Invalid domain: {domain}")

        # Fetch A and AAAA records
        a_records = await query_dnsdb_rrset_name(session, api_key, domain, rrtype='A')
        aaaa_records = await query_dnsdb_rrset_name(session, api_key, domain, rrtype='AAAA')

        # Combine records
        all_records = a_records + aaaa_records
        return all_records

    def process_records(records):
        """
        Process DNSDB records to identify changes over time.
        """
        events = []
        for record in records:
            # Create a sorted tuple of rdata to use as a key
            rdata_set = tuple(sorted(record.rdata))
            event = {
                'date': datetime.utcfromtimestamp(record.time_first),
                'rrtype': record.rrtype,
                'rdata_set': rdata_set,
                'label': ', '.join(record.rdata)  # Only the IP addresses
            }
            events.append(event)

        # Sort events by date
        events.sort(key=lambda x: x['date'])

        # Remove consecutive duplicates (same rdata_set as previous)
        unique_events = []
        previous_rdata_set = None
        for event in events:
            if event['rdata_set'] != previous_rdata_set:
                unique_events.append(event)
                previous_rdata_set = event['rdata_set']

        return unique_events

    def select_events(events, max_events=15):
        """
        Select up to max_events events, evenly distributed over the timeline,
        always including the first and last events.
        """
        total_events = len(events)
        if total_events <= max_events:
            return events, False  # No need to limit events

        # Always include the first and last events
        indices = [0] + [
            round(i * (total_events - 1) / (max_events - 1))
            for i in range(1, max_events - 1)
        ] + [total_events - 1]

        # Remove duplicates in indices
        indices = sorted(set(indices))

        selected_events = [events[i] for i in indices]
        return selected_events, True

    def plot_timeline(events, domain, has_more_events):
        """
        Plot a timeline of DNS record changes and return image bytes.
        """
        import matplotlib
        matplotlib.use('Agg')  # Use non-GUI backend for matplotlib
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        # Prepare data for plotting
        dates = [event['date'] for event in events]
        labels = [event['label'] for event in events]

        # Create levels for label placement to avoid overlap
        levels = np.tile(
            [-5, 5, -4, 4, -3, 3, -2, 2, -1, 1],
            int(np.ceil(len(dates)/10))
        )[:len(dates)]

        # Start plotting
        fig, ax = plt.subplots(figsize=(18, 9))

        # Plot the timeline points
        ax.plot(dates, [0]*len(dates), "-o", color="black", markerfacecolor="white")

        # Set x-ticks to show years
        start_year = min(dates).year
        end_year = max(dates).year + 1  # Include the last year
        xticks = pd.date_range(f"{start_year}-1-1", f"{end_year}-1-1", freq="YS")
        ax.set_xticks(xticks)
        ax.set_xticklabels([date.year for date in xticks])

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

        ax.set_ylim(-7, 7)

        # Annotate the events
        for idx in range(len(events)):
            date = dates[idx]
            label = labels[idx]
            level = levels[idx]
            date_str = date.strftime("%d %b %Y")
            ax.annotate(f"{date_str}\n{label}",
                        xy=(date, 0),
                        xytext=(date, level),
                        arrowprops=dict(arrowstyle="-", color="red", linewidth=0.8),
                        ha="center", va="center", fontsize=10, fontweight='bold', color='royalblue')

        # Style the plot
        ax.spines[["left", "top", "right"]].set_visible(False)
        ax.spines["bottom"].set_position(("data", 0))
        ax.yaxis.set_visible(False)

        # Add a title
        ax.set_title(f"A/AAAA Record Changes for {domain}", pad=10, loc="left",
                     fontsize=20, fontweight="bold", color='royalblue')

        # Add "++" at the top right if there are more events
        if has_more_events:
            ax.text(0.98, 0.98, '++', transform=ax.transAxes, ha='right', va='top',
                    fontsize=16, fontweight='bold', color='red')

        # Adjust layout
        plt.tight_layout()

        # Save the plot to a BytesIO buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=600)
        plt.close(fig)
        buf.seek(0)

        return buf

    async def upload_image_to_s3(image_bytes, domain):
        """
        Upload the image to AWS S3 and return the public URL.
        """
        s3_bucket_name = 'slackrepo'
        s3_key = f'dns_timeline/{domain}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.png'

        s3_client = boto3.client('s3')

        def upload():
            s3_client.upload_fileobj(
                Fileobj=image_bytes,
                Bucket=s3_bucket_name,
                Key=s3_key,
                ExtraArgs={'ContentType': 'image/png', 'ACL': 'public-read'}
            )

        # Run the upload in a thread to avoid blocking the event loop
        await asyncio.to_thread(upload)

        # Generate the public URL
        image_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_key}'

        return image_url
