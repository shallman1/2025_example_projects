# utils/data_utils.py

import csv
from typing import List, Dict, Any, Tuple

def save_results_to_csv(csv_filename: str, search_hash: str, results: List[Dict[str, Any]]) -> None:
    """
    Saves the filtered results to a CSV file.
    """
    fields_to_include = [
        'domain', 'adsense', 'popularity_rank', 'google_analytics',
        'admin_contact', 'billing_contact', 'registrant_contact', 'technical_contact',
        'create_date', 'expiration_date', 'email_domain', 'soa_email', 'ssl_email',
        'ip', 'mx', 'name_server', 'domain_risk', 'redirect', 'registrant_name',
        'registrant_org', 'registrar', 'registrar_status', 'website_response',
        'website_title', 'server_type'
    ]

    filtered_results = []
    fieldnames = set()

    for result in results:
        filtered_result = {}
        for key in result:
            # Exclude count fields
            if key.endswith('_count'):
                continue
            # Include fields that match the specified fields
            for field in fields_to_include:
                if key == field or key.startswith(field + '_'):
                    filtered_result[key] = result[key]
                    fieldnames.add(key)
                    break
        filtered_results.append(filtered_result)

    fieldnames = sorted(fieldnames)

    # Open the CSV file for writing
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        # Create a CSV DictWriter object
        writer = csv.DictWriter(csvfile, fieldnames=['search_hash'] + fieldnames)

        # Write the header row
        writer.writeheader()

        # Write the data rows
        for result in filtered_results:
            row = {'search_hash': search_hash}
            row.update(result)
            writer.writerow(row)

def read_results_from_csv(csv_filename: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Reads results from a CSV file and reconstructs the list of results.
    """
    results = []
    search_hash = ''
    with open(csv_filename, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Extract search_hash from the row
            if 'search_hash' in row:
                if not search_hash:
                    search_hash = row['search_hash']
                else:
                    # Ensure all rows have the same search_hash
                    if search_hash != row['search_hash']:
                        raise ValueError("Inconsistent search_hash in CSV file.")
            else:
                raise ValueError("search_hash not found in CSV file.")
            # Remove 'search_hash' from the result
            result = dict(row)
            result.pop('search_hash', None)
            results.append(result)
    return search_hash, results


def compare_results(old_results: List[Dict[str, Any]], new_results: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """
    Compares old and new results to identify added, removed, and modified entries.
    """
    changes = {
        'added': [],
        'removed': [],
        'modified': []
    }

    # Create dictionaries for quick lookup based on the 'domain' field
    old_dict = {item['domain']: item for item in old_results}
    new_dict = {item['domain']: item for item in new_results}

    # Find added and removed domains
    old_domains = set(old_dict.keys())
    new_domains = set(new_dict.keys())

    added_domains = new_domains - old_domains
    removed_domains = old_domains - new_domains

    for domain in added_domains:
        changes['added'].append(new_dict[domain])

    for domain in removed_domains:
        changes['removed'].append(old_dict[domain])

    # Specify the fields to compare
    fields_to_include = [
        'domain', 'adsense', 'popularity_rank', 'google_analytics',
        'admin_contact', 'billing_contact', 'registrant_contact', 'technical_contact',
        'create_date', 'expiration_date', 'email_domain', 'soa_email', 'ssl_email',
        'ip', 'mx', 'name_server', 'domain_risk', 'redirect', 'registrant_name',
        'registrant_org', 'registrar', 'registrar_status', 'website_response',
        'website_title', 'server_type'
    ]

    # Find modified domains
    common_domains = old_domains & new_domains
    for domain in common_domains:
        old_item = old_dict[domain]
        new_item = new_dict[domain]
        differences = {}

        # Compare fields
        old_keys = set(old_item.keys())
        new_keys = set(new_item.keys())
        all_keys = old_keys.union(new_keys)

        # Exclude 'count' fields and only include specified fields
        for key in all_keys:
            if key.endswith('_count'):
                continue
            # Check if the key corresponds to the fields we care about
            field_matched = False
            for field in fields_to_include:
                if key == field or key.startswith(field + '_'):
                    field_matched = True
                    break
            if not field_matched:
                continue

            old_value = old_item.get(key, '')
            new_value = new_item.get(key, '')

            # Handle lists
            if isinstance(old_value, list) and isinstance(new_value, list):
                old_set = set(old_value)
                new_set = set(new_value)
                added_items = new_set - old_set
                removed_items = old_set - new_set
                if added_items or removed_items:
                    differences[key] = {
                        'added': list(added_items),
                        'removed': list(removed_items)
                    }
            else:
                # For other data types, compare values as strings
                if str(old_value) != str(new_value):
                    differences[key] = {
                        'old': old_value,
                        'new': new_value
                    }

        if differences:
            changes['modified'].append({
                'domain': domain,
                'differences': differences
            })

    return changes
