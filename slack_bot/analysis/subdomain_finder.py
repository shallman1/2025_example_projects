# analysis/subdomain_finder.py

import asyncio
import aiohttp
import json
import time
from collections import defaultdict

API_URL = 'https://api.dnsdb.info/dnsdb/v2/lookup/rrset/name/*.{domain}/ANY?limit=100000&time_last_after={time_last_after}'

# Semaphore to limit concurrency to 10 requests
sem = asyncio.Semaphore(10)

class Node:
    def __init__(self, name):
        self.name = name
        self.children = {}
        self.rdata = set()
        self.count = 0  # Initialize count
        self.is_leaf = True  # Assume node is a leaf until it has children
        self.time_last = 0  # Initialize time_last

def get_subdomain_labels(domain, rrname):
    # Remove trailing dots
    domain = domain.rstrip('.')
    rrname = rrname.rstrip('.')
    if rrname == domain:
        return []
    elif rrname.endswith('.' + domain):
        subdomain_part = rrname[:-(len(domain)+1)]
        labels = subdomain_part.split('.')
        return labels
    else:
        # rrname does not belong to the domain
        return None

def process_response(domain, text, tree):
    lines = text.strip().split('\n')
    allowed_rrtypes = {'A', 'AAAA', 'CNAME'}  # Exclude TXT from rdata collection
    for line in lines:
        if line.strip() == '':
            continue
        data = json.loads(line)
        if 'obj' in data:
            obj = data['obj']
            rrtype = obj.get('rrtype', '')
            if rrtype not in allowed_rrtypes and rrtype != 'TXT':
                continue  # Skip unwanted rrtypes
            rrname = obj.get('rrname', '')
            rdata = obj.get('rdata', [])
            count = obj.get('count', 0)
            time_last = obj.get('time_last', 0)
            labels = get_subdomain_labels(domain, rrname)
            if labels is not None:
                # Build the tree
                current_node = tree[domain]
                node_path = [current_node]  # Keep track of nodes from root to leaf
                # Process labels in reverse order to build correct hierarchy
                for label in reversed(labels):
                    current_node.is_leaf = False  # Node has children, so it's not a leaf
                    if label not in current_node.children:
                        current_node.children[label] = Node(label)
                    current_node = current_node.children[label]
                    node_path.append(current_node)
                # Only collect rdata if rrtype is not 'TXT'
                if rrtype != 'TXT':
                    current_node.rdata.update(rdata)
                # Add count to all nodes in the path
                for node in node_path:
                    node.count += count
                # Update time_last
                if time_last > current_node.time_last:
                    current_node.time_last = time_last

def collect_fqdns_from_tree(tree, domains):
    fqdns = {}
    for domain in domains:
        root_node = tree[domain]
        fqdns.update(collect_fqdns(root_node, [root_node.name]))
    return fqdns  # fqdns is a dict of fqdn -> time_last

def collect_fqdns(node, domain_path):
    fqdns = {}
    child_nodes = list(node.children.values())
    for child_node in child_nodes:
        child_name = child_node.name
        domain_path.append(child_name)
        fqdn = '.'.join(reversed(domain_path))
        # Collect the fqdn and time_last
        fqdns[fqdn] = child_node.time_last
        # Recursively collect from children
        child_fqdns = collect_fqdns(child_node, domain_path)
        fqdns.update(child_fqdns)
        domain_path.pop()
    return fqdns

async def fetch_domain(domain, session, time_last_after, api_key):
    url = API_URL.format(domain=domain, time_last_after=time_last_after)
    headers = {
        'Accept': 'application/x-ndjson',
        'X-API-Key': api_key
    }
    async with sem:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                text = await response.text()
                return domain, text
            else:
                print(f"Failed to fetch {domain}: HTTP {response.status}")
                return domain, None

async def run_subdomain_finder(domains, api_key, time_last_after=None):
    if time_last_after is None:
        # Compute default time_last_after (30 days before current time)
        current_time = int(time.time())
        thirty_days = 30 * 24 * 60 * 60
        time_last_after = current_time - thirty_days

    tree = {}
    async with aiohttp.ClientSession() as session:
        tasks = []
        for domain in domains:
            tree[domain] = Node(domain)
            tasks.append(fetch_domain(domain, session, time_last_after, api_key))
        responses = await asyncio.gather(*tasks)
        for domain, text in responses:
            if text:
                process_response(domain, text, tree)
    # Collect FQDNs
    fqdns = collect_fqdns_from_tree(tree, domains)
    # Generate HTML report
    html_report = generate_html_report(tree, domains)
    return tree, fqdns

def generate_html_report(tree, domains):
    html_parts = []
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html lang="en">')
    html_parts.append('<head>')
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append('<title>DNSDB Passive DNS Report</title>')
    html_parts.append('<style>')
    html_parts.append('body { font-family: Arial, sans-serif; }')
    html_parts.append('details { margin-left: 20px; }')
    html_parts.append('summary { font-weight: bold; cursor: pointer; }')
    html_parts.append('p { margin-left: 20px; }')
    html_parts.append('</style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    html_parts.append('<h1>DNSDB Passive DNS Report</h1>')

    for domain in domains:
        root_node = tree[domain]
        summary_text = f"{root_node.name} (count: {root_node.count})"
        html_parts.append(f'<details closed>')
        html_parts.append(f'<summary>{summary_text}</summary>')
        html_parts.extend(generate_html_tree(root_node, [root_node.name]))
        html_parts.append(f'</details>')

    html_parts.append('</body>')
    html_parts.append('</html>')
    return '\n'.join(html_parts)

def generate_html_tree(node, domain_path):
    html_parts = []
    child_nodes = list(node.children.values())
    child_nodes.sort(key=lambda x: x.count, reverse=True)
    for child_node in child_nodes:
        child_name = child_node.name
        domain_path.append(child_name)
        fqdn = '.'.join(reversed(domain_path))
        summary_text = f"{fqdn} (count: {child_node.count})"
        if child_node.rdata:
            rdata_text = limit_rdata(child_node.rdata)
            summary_text += f' : {rdata_text}'
        if child_node.children:
            html_parts.append('<details closed>')
            html_parts.append(f'<summary>{summary_text}</summary>')
            html_parts.extend(generate_html_tree(child_node, domain_path))
            html_parts.append('</details>')
        else:
            html_parts.append(f'<p>{summary_text}</p>')
        domain_path.pop()
    return html_parts

def limit_rdata(rdata_set):
    rdata_list = sorted(rdata_set)
    if len(rdata_list) > 5:
        return ', '.join(rdata_list[:5]) + ', +'
    else:
        return ', '.join(rdata_list)

