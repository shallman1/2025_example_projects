# commands/dga.py

from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from utils.validation_utils import is_valid_domain
from utils.api_utils import query_dnsdb_rrset_name
from models.dnsdb_models import DnsdbRecord
import aiohttp
import time
from slack_sdk.models.blocks import (
    SectionBlock,
    ActionsBlock,
    ButtonElement,
    DividerBlock,
)
from slack_sdk.models.views import View
from dgaintel import get_prob 
import os
import asyncio
import aiofiles
from functools import lru_cache
def register_dga_command(app: AsyncApp):

    @app.command("/dga")
    async def handle_dga_command(ack, say, command, client, logger):
        await ack()

        channel_id = command['channel_id']
        user_id = command['user_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the domain from the command text
        domain = command['text'].strip()

        if not domain:
            await say("Please provide a domain. Usage: /dga <domain>")
            return

        if not is_valid_domain(domain):
            await say(f"The domain '{domain}' is not valid. Please provide a valid domain.")
            return

        try:
            # Query DNSDB for subdomains
            rrnames = await get_subdomains(domain)

            if not rrnames:
                await say(f"No subdomains found for domain '{domain}'.")
                return

            # Analyze the domains for potential DGA behavior using dgaintel
            dga_results = await analyze_domains_with_dgaintel(rrnames)  # Note the 'await' keyword

            if not dga_results:
                await say(f"No suspected DGA domains found for '{domain}'.")
                return

            # Cache the results for pagination
            cache_key = f"dga_{user_id}_{domain}"
            app.cache[cache_key] = dga_results  # Cache for 1 hour (TTL is set in TTLCache)

            # Send the initial message with the number of suspected DGAs and a button to display results
            total_suspected = len(dga_results)
            await say(
                text=f"Found {total_suspected} suspected DGA domains for '{domain}'.",
                blocks=[
                    SectionBlock(text=f"*Found {total_suspected} suspected DGA domains for '{domain}'.*").to_dict(),
                    ActionsBlock(
                        elements=[
                            ButtonElement(
                                text="View Results",
                                action_id="show_dga_results",
                                value=cache_key
                            )
                        ]
                    ).to_dict()
                ]
            )

        except Exception as e:
            logger.error(f"Error in /dga command: {e}")
            await say(f"An error occurred during DGA analysis: {str(e)}")

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

    async def get_subdomains(domain):
        """
        Queries DNSDB for subdomains of the given domain.
        Returns a list of rrnames.
        """
        from config import DNSDB_API_KEY

        # Compute time_last_after (1 year before current time)
        current_time = int(time.time())
        one_year = 365 * 24 * 60 * 60
        time_last_after = current_time - one_year

        async with aiohttp.ClientSession() as session:
            # Prepare the query
            query = f'*.{domain}'
            rrtype = 'ANY'
            limit = 100000

            # Query for subdomains
            records = await query_dnsdb_rrset_name(
                session,
                DNSDB_API_KEY,
                query,
                rrtype=rrtype,
                limit=limit,
                time_last_after=time_last_after
            )

            # Extract rrnames
            rrnames = set()
            for record in records:
                rrname = record.rrname.rstrip('.')
                rrnames.add(rrname)

            return list(rrnames)
    async def analyze_domains_with_dgaintel(domains):
        MAX_LABEL_LENGTH = 82  # Limit label length to 82 characters

        # Load and cache known good labels
        known_good_labels = load_known_good_labels()

        labels_to_analyze = set()
        domain_label_map = {}  # Map labels back to their domains

        for domain in domains:
            labels = domain.split('.')
            subdomain_labels = labels[:-2] if len(labels) >= 2 else []

            for label in subdomain_labels:
                label_lower = label.lower()
                if (not label.startswith('_') and
                    len(label) <= MAX_LABEL_LENGTH and
                    label_lower not in known_good_labels):
                    labels_to_analyze.add(label)
                    domain_label_map.setdefault(label, set()).add(domain)

        labels_to_analyze = list(labels_to_analyze)

        # Prepare log entries
        log_entries = ['Label\tProbability\tDomains\n']

        batch_size = 500
        batches = [labels_to_analyze[i:i + batch_size] for i in range(0, len(labels_to_analyze), batch_size)]

        # Use asyncio to process batches concurrently
        tasks = [process_batch(batch, domain_label_map) for batch in batches]
        batch_results = await asyncio.gather(*tasks)

        suspected_dgas = []
        for batch_dgas, batch_logs in batch_results:
            suspected_dgas.extend(batch_dgas)
            log_entries.extend(batch_logs)

        # Write all log entries at once
        async with aiofiles.open('prob_log.txt', 'w') as f:
            await f.writelines(log_entries)

        return suspected_dgas

    async def process_batch(batch, domain_label_map):
        suspected_dgas = []
        log_entries = []

        # Run get_prob in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, get_prob, batch)

        if isinstance(results, list):
            for label, probability in results:
                probability = float(probability)
                domains = ', '.join(domain_label_map.get(label, []))
                log_entries.append(f"{label}\t{probability:.4f}\t{domains}\n")

                if probability >= 0.97:
                    dga_type = classify_dga_type(probability)
                    for domain in domain_label_map.get(label, []):
                        suspected_dgas.append({
                            'domain': domain,
                            'label': label,
                            'probability': round(probability, 4),
                            'dga_type': dga_type
                        })
        else:
            label = batch[0]
            probability = float(results)
            domains = ', '.join(domain_label_map.get(label, []))
            log_entries.append(f"{label}\t{probability:.4f}\t{domains}\n")

            if probability >= 0.97:
                dga_type = classify_dga_type(probability)
                for domain in domain_label_map.get(label, []):
                    suspected_dgas.append({
                        'domain': domain,
                        'label': label,
                        'probability': round(probability, 4),
                        'dga_type': dga_type
                    })

        return suspected_dgas, log_entries

    @lru_cache(maxsize=1)
    def load_known_good_labels():
        """
        Loads known good labels from the 'known_good_labels.txt' file.
        Returns a set of labels.
        """
        try:
            with open('known_good_labels.txt', 'r') as file:
                labels = {label.strip().lower() for label in file if label.strip()}
                return labels
        except Exception as e:
            print(f"Error loading known good labels: {e}")
            return set()

    def classify_dga_type(probability):
        """
        Classifies the DGA type based on probability.
        Since dgaintel does not provide DGA types, we'll label them as 'Suspected DGA'.
        """
        return 'Suspected DGA'

    # Action handler for pagination
    @app.action("show_dga_results")
    async def handle_show_dga_results(ack, body, client):
        await ack()
        user_id = body['user']['id']
        trigger_id = body['trigger_id']
        cache_key = body['actions'][0]['value']

        # Retrieve cached results
        dga_results = app.cache.get(cache_key, [])

        # Display the first page
        await open_dga_results_modal(client, trigger_id, dga_results, page=1, cache_key=cache_key)

    async def open_dga_results_modal(client, trigger_id, dga_results, page, cache_key, view_id=None):
        total_results = len(dga_results)
        results_per_page = 20
        total_pages = min((total_results + results_per_page - 1) // results_per_page, 2)  # Max 2 pages

        start_index = (page - 1) * results_per_page
        end_index = start_index + results_per_page
        page_results = dga_results[start_index:end_index]

        blocks = []

        for result in page_results:
            blocks.append(SectionBlock(
                text=f"*Domain:* `{result['domain']}`\n"
                     f"*Suspicious Label:* `{result['label']}`\n"
                     f"*DGA Type:* {result['dga_type']}`\n"
                     f"*Probability:* `{result['probability']}`"
            ).to_dict())
            blocks.append(DividerBlock().to_dict())

        # Add pagination buttons if necessary
        actions = []
        if page > 1:
            actions.append(
                ButtonElement(
                    text="Previous",
                    action_id="change_dga_page",
                    value=f"{page - 1}|{cache_key}"
                )
            )
        if page < total_pages:
            actions.append(
                ButtonElement(
                    text="Next",
                    action_id="change_dga_page",
                    value=f"{page + 1}|{cache_key}"
                )
            )
        if actions:
            blocks.append(ActionsBlock(elements=actions).to_dict())

        modal_view = View(
            type="modal",
            title="DGA Analysis Results",
            blocks=blocks,
            close={
                "type": "plain_text",
                "text": "Close"
            }
        )

        if view_id:
            # Update the existing modal
            await client.views_update(
                view_id=view_id,
                view=modal_view.to_dict()
            )
        else:
            # Open a new modal
            await client.views_open(
                trigger_id=trigger_id,
                view=modal_view.to_dict()
            )

    @app.action("change_dga_page")
    async def handle_change_dga_page(ack, body, client):
        await ack()
        trigger_id = body['trigger_id']
        action_value = body['actions'][0]['value']
        page_str, cache_key = action_value.split('|')
        page = int(page_str)
        view_id = body['view']['id']  # Get the view ID from the current modal

        # Retrieve cached results
        dga_results = app.cache.get(cache_key, [])

        # Update the modal with the new page
        await open_dga_results_modal(client, trigger_id, dga_results, page, cache_key, view_id=view_id)
