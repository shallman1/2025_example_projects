# analysis/dns_history.py

import asyncio
from typing import List, Dict, Set
from models.dnsdb_models import DnsdbRecord
from utils.api_utils import query_dnsdb_rrset_name, query_dnsdb_rdata_ip
import aiohttp

async def run_dns_history_analysis(domains: List[str], ips: List[str], api_key: str):
    data = {}

    async with aiohttp.ClientSession() as session:
        tasks = []

        async def fetch_domain_data(domain):
            records = await query_dnsdb_rrset_name(session, api_key, domain)
            data[domain] = records

        async def fetch_ip_data(ip):
            records = await query_dnsdb_rdata_ip(session, api_key, ip)
            data[ip] = records

        for domain in domains:
            tasks.append(fetch_domain_data(domain))

        for ip in ips:
            tasks.append(fetch_ip_data(ip))

        await asyncio.gather(*tasks)

    # Collect IPs and hostnames
    ip_occurrences: Dict[str, Set[str]] = {}
    hostname_occurrences: Dict[str, Set[str]] = {}

    for item, records in data.items():
        for record in records:
            # Collect IP addresses
            if record.rrtype in ['A', 'AAAA']:
                for ip in record.rdata:
                    ip_occurrences.setdefault(ip, set()).add(item)
            # Collect hostnames from rdata and rrname
            elif record.rrtype in ['CNAME', 'NS', 'MX', 'PTR', 'SOA', 'SRV', 'TXT', 'ANY']:
                for hostname in record.rdata:
                    hostname_occurrences.setdefault(hostname.rstrip('.'), set()).add(item)
            # Include rrname as a hostname
            hostname_occurrences.setdefault(record.rrname.rstrip('.'), set()).add(item)

    # Find overlapping IPs and hostnames
    overlapping_ips = {ip: items for ip, items in ip_occurrences.items() if len(items) > 1}
    overlapping_hostnames = {hostname: items for hostname, items in hostname_occurrences.items() if len(items) > 1}

    overlapping_data = {
        'overlapping_ips': overlapping_ips,
        'overlapping_hostnames': overlapping_hostnames
    }

    return overlapping_data
