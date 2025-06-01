# commands/subdomains.py

import asyncio
import aiohttp
from slack_sdk.errors import SlackApiError
from slack_bolt.async_app import AsyncApp
from config import DNSDB_API_KEY
from slack_sdk.models.blocks import (
    SectionBlock,
    ActionsBlock,
    ButtonElement,
)
import time

def register_subdomains_command(app: AsyncApp):

    @app.command("/subdomains")
    async def handle_subdomains_command(ack, say, command, client, logger):
        await ack()

        channel_id = command['channel_id']
        user_id = command['user_id']

        # Try to join the channel if not already in it
        if not await ensure_bot_in_channel(client, channel_id, say):
            return

        # Extract the domains from the command text
        domains_text = command['text'].strip()

        if not domains_text:
            await say("Please provide at least one domain. Usage: /subdomains <domain1,domain2,...>")
            return

        domains = [domain.strip() for domain in domains_text.split(',') if domain.strip()]

        try:
            # Run the subdomain finder
            tree = await get_subdomains_tree(domains)

            if not tree:
                await say(f"No subdomains found for domains: {', '.join(domains)}.")
                return

            # Flatten the tree to get a list of FQDNs with indentation
            fqdn_list = flatten_tree_with_indentation(tree)

            # Initialize the pagination state (starting with page 1)
            state = {
                'current_page': 1,
                'fqdn_list': fqdn_list,
            }

            # Cache the state for the user
            cache_key = f"subdomains_{user_id}_{int(time.time())}"
            app.cache[cache_key] = state  # Cache with appropriate TTL

            # Send the initial report
            response = await send_subdomains_report(client, channel_id, cache_key, state)
            # Store the timestamp of the message to use it for updating
            app.cache[cache_key]['message_ts'] = response['ts']

        except Exception as e:
            logger.error(f"Error in /subdomains command: {e}")
            await say(f"An error occurred during subdomain analysis: {str(e)}")

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

    async def get_subdomains_tree(domains):
        """
        Retrieves subdomains for the given list of domains and builds a tree structure.
        """
        from utils.api_utils import query_dnsdb_rrset_name

        # Compute time_last_after (1 year before current time)
        current_time = int(time.time())
        one_year = 365 * 24 * 60 * 60
        time_last_after = current_time - one_year

        async with aiohttp.ClientSession() as session:
            # Prepare queries for all domains
            tasks = []
            for domain in domains:
                query = f'*.{domain}'
                rrtype = 'ANY'
                limit = 100000
                tasks.append(query_dnsdb_rrset_name(
                    session,
                    DNSDB_API_KEY,
                    query,
                    rrtype=rrtype,
                    limit=limit,
                    time_last_after=time_last_after
                ))

            # Run all queries concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect rrnames
            rrnames = set()
            for res in results:
                if isinstance(res, Exception):
                    print(f"Error fetching subdomains: {res}")
                    continue
                for record in res:
                    rrname = record.rrname.rstrip('.')
                    rrnames.add(rrname)

            # Include the original domains
            rrnames.update(domains)

            # Build the tree
            tree = build_subdomain_tree(rrnames)
            return tree

    def build_subdomain_tree(rrnames):
        """
        Builds a tree structure from a list of rrnames.
        """
        tree = {}
        for rrname in rrnames:
            labels = rrname.split('.')
            
            # Skip the TLD level
            if labels[-1] == "com":
                labels = labels[:-1]

            node = tree
            for label in reversed(labels):
                if label not in node:
                    node[label] = {}
                node = node[label]
        return tree

    def flatten_tree_with_indentation(tree, prefix=""):
        """
        Flattens the tree into a list of FQDNs with hierarchical indentation.
        """
        fqdn_list = []

        def _flatten(node, current_path, level):
            for label, child_node in node.items():
                if current_path:
                    fqdn = f"{label}.{current_path}"
                else:
                    fqdn = label

                # Create the indentation string using "|-" characters
                indentation = "|-" * level

                # Append the formatted FQDN with the correct level of indentation
                fqdn_list.append(f"{indentation} {fqdn}")

                # Recursively flatten the child nodes
                _flatten(child_node, fqdn, level + 1)

        # Start flattening from the root of the tree
        _flatten(tree, prefix, level=0)
        return fqdn_list


    async def send_subdomains_report(client, channel_id, cache_key, state):
        """
        Sends a markdown formatted report of subdomains for the given page.
        """
        current_page = state['current_page']
        fqdn_list = state['fqdn_list']

        # Determine the indices for the current page
        items_per_page = 15
        start_idx = (current_page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        # Slice the list to get the current page's items
        current_page_items = fqdn_list[start_idx:end_idx]

        # Generate the markdown report
        report = "\n".join(current_page_items)
        total_pages = (len(fqdn_list) + items_per_page - 1) // items_per_page

        # Create pagination buttons if applicable
        elements = []
        if current_page > 1:
            elements.append(ButtonElement(
                text="Previous",
                action_id=f"paginate_subdomains_prev",
                value=f"{cache_key}|prev",
                style="primary"
            ).to_dict())

        if current_page < total_pages:
            elements.append(ButtonElement(
                text="Next",
                action_id=f"paginate_subdomains_next",
                value=f"{cache_key}|next",
                style="primary"
            ).to_dict())

        # Build the blocks for Slack message
        blocks = [
            SectionBlock(text=f"*Subdomain Report (Page {current_page}/{total_pages})*\n```{report}```").to_dict()
        ]

        # Add the actions block only if there are elements (buttons)
        if elements:
            blocks.append(ActionsBlock(elements=elements).to_dict())

        # Send or update the message
        if 'message_ts' in state:
            # Update the existing message
            response = await client.chat_update(
                channel=channel_id,
                ts=state['message_ts'],
                text="Subdomain Report",
                blocks=blocks
            )
        else:
            # Send a new message
            response = await client.chat_postMessage(
                channel=channel_id,
                text="Subdomain Report",
                blocks=blocks
            )
        return response

    # Register action handlers for pagination
    @app.action("paginate_subdomains_prev")
    async def handle_paginate_subdomains_prev(ack, body, client):
        await handle_pagination_action(ack, body, client, "prev")

    @app.action("paginate_subdomains_next")
    async def handle_paginate_subdomains_next(ack, body, client):
        await handle_pagination_action(ack, body, client, "next")

    async def handle_pagination_action(ack, body, client, direction):
        await ack()
        user_id = body['user']['id']
        action_value = body['actions'][0]['value']
        cache_key, _ = action_value.split('|')

        # Retrieve cached state
        state = app.cache.get(cache_key, {})
        if not state:
            await client.chat_postMessage(channel=body['channel']['id'], text="Session expired. Please run the command again.")
            return

        # Update the current page based on the direction
        if direction == "next":
            state['current_page'] += 1
        elif direction == "prev" and state['current_page'] > 1:
            state['current_page'] -= 1

        # Update the cache with the new state
        app.cache[cache_key] = state

        # Send the updated report
        channel_id = body['channel']['id']
        await send_subdomains_report(client, channel_id, cache_key, state)

# Register the command with the app instance
