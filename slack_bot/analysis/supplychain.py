# analysis/supplychain.py

import asyncio
import aiohttp
import time
from models.dnsdb_models import DnsdbRecord
from utils.api_utils import query_dnsdb_rrset_name
import re

async def run_supply_chain_analysis(target_domains, api_key, source_labels=None, time_last_after=None):
    if time_last_after is None:
        # Compute default time_last_after (1 year before current time)
        current_time = int(time.time())
        one_year = 365 * 24 * 60 * 60  # Number of seconds in a year
        time_last_after = current_time - one_year

    # Collect labels and their most recent FQDNs
    label_fqdn_time = {}  # {label: (fqdn, time_last)}

    async with aiohttp.ClientSession() as session:
        tasks = []
        for domain in target_domains:
            tasks.append(fetch_subdomains(domain, session, time_last_after, api_key))
        responses = await asyncio.gather(*tasks)
        for records in responses:
            for record in records:
                fqdn = record.rrname.rstrip('.')
                labels = fqdn.split('.')
                time_last = record.time_last or 0
                for label in labels:
                    label_lower = label.lower()
                    if source_labels is not None and label_lower not in source_labels:
                        continue
                    # Keep the FQDN with the most recent time_last for each label
                    if label_lower not in label_fqdn_time or label_fqdn_time[label_lower][1] < time_last:
                        label_fqdn_time[label_lower] = (fqdn, time_last)
    return label_fqdn_time

async def fetch_subdomains(domain, session, time_last_after, api_key):
    # Use the dnsdb data model and query function
    records = await query_dnsdb_rrset_name(
        session, api_key, '*.' + domain, limit=100000, time_last_after=time_last_after
    )
    return records

