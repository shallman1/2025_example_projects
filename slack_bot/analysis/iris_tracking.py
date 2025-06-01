# analysis/iris_tracking.py

import os
import csv
import json
import asyncio
from datetime import datetime
from models.iris_investigate_models import IrisInvestigateResponse
from config import IRIS_API_KEY, IRIS_USER
from utils.iris_api_utils import query_iris_api
from slack_sdk.web.async_client import AsyncWebClient

TRACKING_DIR = 'tracking_data'  # Directory to store tracking CSV files

if not os.path.exists(TRACKING_DIR):
    os.makedirs(TRACKING_DIR)

async def start_tracking(user_id, search_hash, channel_id):
    # Query the Iris Investigate API
    initial_data = await query_iris_api_with_search_hash(search_hash)

    # Store the data in a CSV file
    tracking_file = os.path.join(TRACKING_DIR, f"{user_id}_{search_hash}.csv")
    with open(tracking_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'channel_id', 'data']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            'timestamp': datetime.utcnow().isoformat(),
            'channel_id': channel_id,
            'data': json.dumps(initial_data)
        })

async def query_iris_api_with_search_hash(search_hash):
    # Use your existing function to query the Iris API
    response_data = await query_iris_api(IRIS_API_KEY, IRIS_USER, search_hash)
    return response_data

async def check_for_updates(client: AsyncWebClient):
    # This function will be called daily
    tracking_files = [f for f in os.listdir(TRACKING_DIR) if f.endswith('.csv')]
    for filename in tracking_files:
        tracking_file = os.path.join(TRACKING_DIR, filename)
        with open(tracking_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            if not rows:
                continue
            last_entry = rows[-1]
            user_id, search_hash = filename.replace('.csv', '').split('_', 1)
            channel_id = last_entry['channel_id']
            old_data = json.loads(last_entry['data'])

            # Query the Iris Investigate API
            new_data = await query_iris_api_with_search_hash(search_hash)

            # Compare the new data with the cached data
            changes = compare_data(old_data, new_data)

            if changes:
                # Alert the user
                await client.chat_postMessage(
                    channel=channel_id,
                    text=f"Changes detected for your tracked search hash `{search_hash}`:\n{changes}"
                )
                # Update the cached data
                with open(tracking_file, 'a', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['timestamp', 'channel_id', 'data']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerow({
                        'timestamp': datetime.utcnow().isoformat(),
                        'channel_id': channel_id,
                        'data': json.dumps(new_data)
                    })

def compare_data(old_data, new_data):
    # Implement comparison logic
    # Return a string describing the changes, or None if no changes

    # Compare domains
    old_domains = set(result['domain'] for result in old_data['response']['results'])
    new_domains = set(result['domain'] for result in new_data['response']['results'])

    added_domains = new_domains - old_domains
    removed_domains = old_domains - new_domains

    changes = []
    if added_domains:
        changes.append(f"*New domains added:* {', '.join(added_domains)}")
    if removed_domains:
        changes.append(f"*Domains removed:* {', '.join(removed_domains)}")

    # Compare details for each domain
    old_results = {result['domain']: result for result in old_data['response']['results']}
    new_results = {result['domain']: result for result in new_data['response']['results']}

    for domain in new_domains & old_domains:
        old_result = old_results[domain]
        new_result = new_results[domain]

        domain_changes = compare_domain_data(old_result, new_result)
        if domain_changes:
            changes.append(f"*Changes for domain `{domain}`:*\n{domain_changes}")

    return '\n'.join(changes) if changes else None

def compare_domain_data(old_result, new_result):
    changes = []

    # Compare IP addresses
    old_ips = set(ip['address']['value'] for ip in old_result.get('ip', []))
    new_ips = set(ip['address']['value'] for ip in new_result.get('ip', []))

    added_ips = new_ips - old_ips
    removed_ips = old_ips - new_ips

    if added_ips:
        changes.append(f"  - New IPs: {', '.join(added_ips)}")
    if removed_ips:
        changes.append(f"  - IPs removed: {', '.join(removed_ips)}")

    # Compare registrant name
    old_registrant = old_result.get('registrant_name', {}).get('value', '')
    new_registrant = new_result.get('registrant_name', {}).get('value', '')

    if old_registrant != new_registrant:
        changes.append(f"  - Registrant name changed from `{old_registrant}` to `{new_registrant}`")

    # Handle lists where order doesn't matter (e.g., name servers)
    old_ns = set(ns['host']['value'] for ns in old_result.get('name_server', []))
    new_ns = set(ns['host']['value'] for ns in new_result.get('name_server', []))

    added_ns = new_ns - old_ns
    removed_ns = old_ns - new_ns

    if added_ns:
        changes.append(f"  - New name servers: {', '.join(added_ns)}")
    if removed_ns:
        changes.append(f"  - Name servers removed: {', '.join(removed_ns)}")

    # Compare other fields as needed

    return '\n'.join(changes) if changes else None
