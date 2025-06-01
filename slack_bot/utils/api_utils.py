# utils/api_utils.py

import aiohttp
import asyncio
import json
from typing import List
from models.dnsdb_models import DnsdbRecord
from utils.flatten_utils import flatten_json

async def query_dnsdb(session, api_key, url):
    headers = {
        'Accept': 'application/x-ndjson',
        'X-API-Key': api_key
    }
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            text = await response.text()
            raise Exception(f"Error {response.status}: {text}")
        text = await response.text()
        # Parse NDJSON
        records = []
        for line in text.strip().split('\n'):
            if not line.strip():
                continue
            data = json.loads(line)
            if 'obj' in data:
                obj = data['obj']
                record = DnsdbRecord(
                    rrname=obj.get('rrname', '').rstrip('.'),
                    rrtype=obj.get('rrtype', ''),
                    rdata=[r.rstrip('.') for r in obj.get('rdata', [])],
                    time_first=obj.get('time_first'),
                    time_last=obj.get('time_last'),
                    count=obj.get('count'),
                    bailiwick=obj.get('bailiwick', '').rstrip('.') if obj.get('bailiwick') else None
                )
                records.append(record)
        return records

async def query_dnsdb_rrset_name(session, api_key, domain, rrtype='ANY', limit=10000, **params):
    # Build the URL with optional parameters
    url = f'https://api.dnsdb.info/dnsdb/v2/lookup/rrset/name/{domain}/{rrtype}?limit={limit}'
    # Append additional parameters
    for key, value in params.items():
        url += f'&{key}={value}'
    records = await query_dnsdb(session, api_key, url)
    return records

async def query_dnsdb_rdata_ip(session, api_key, ip, limit=10000):
    url = f'https://api.dnsdb.info/dnsdb/v2/lookup/rdata/ip/{ip}/?limit={limit}'
    records = await query_dnsdb(session, api_key, url)
    return records

async def query_iris_api(api_key, api_username, search_hash):
    url = 'https://api.domaintools.com/v1/iris-investigate/'
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'search_hash': search_hash,
        'api_key': api_key,
        'api_username': api_username
    }

    all_results = []
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.post(url, headers=headers, data=data) as response:
                response_data = await response.json()

                if 'response' not in response_data or 'results' not in response_data['response']:
                    print("Error in API response:", response_data)
                    break

                # Normalize each result
                for result in response_data['response']['results']:
                    normalized_result = flatten_json(result)
                    all_results.append(normalized_result)

                if not response_data['response'].get('has_more_results', False):
                    break

                data['position'] = response_data['response'].get('position', '')

    return all_results