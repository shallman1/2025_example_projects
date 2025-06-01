# tasks/scheduled_tasks.py

import os
import glob
import csv
from config import IRIS_API_KEY, IRIS_USER
from utils.data_utils import save_results_to_csv, read_results_from_csv, compare_results
from utils.api_utils import query_iris_api

async def send_changes_to_user(app, user_id, changes):
    """
    Sends a CSV file with the changes detected to the user via direct message.
    """
    # Build a CSV file with the changes
    changes_filename = f"{user_id}_changes.csv"
    with open(changes_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Change Type', 'Domain', 'Field', 'Details'])
        # Write added domains
        for result in changes.get('added', []):
            writer.writerow(['Added', result.get('domain', ''), '', ''])
        # Write removed domains
        for result in changes.get('removed', []):
            writer.writerow(['Removed', result.get('domain', ''), '', ''])
        # Write modified domains
        for item in changes.get('modified', []):
            domain = item['domain']
            differences = item['differences']
            for field, diff in differences.items():
                if isinstance(diff, dict) and ('added' in diff or 'removed' in diff):
                    added_items = diff.get('added', [])
                    removed_items = diff.get('removed', [])
                    details = ''
                    if added_items:
                        details += f"Added: {', '.join(added_items)}"
                    if removed_items:
                        if details:
                            details += '; '
                        details += f"Removed: {', '.join(removed_items)}"
                    writer.writerow(['Modified', domain, field, details])
                else:
                    old_value = str(diff.get('old', ''))
                    new_value = str(diff.get('new', ''))
                    writer.writerow(['Modified', domain, field, f"Old: {old_value}; New: {new_value}"])

    # Send the CSV file to the user via direct message
    dm = await app.client.conversations_open(users=user_id)
    dm_channel_id = dm['channel']['id']

    # Upload the CSV file to Slack
    with open(changes_filename, 'rb') as file_content:
        await app.client.files_upload_v2(
            channels=dm_channel_id,
            file=file_content,
            filename='changes.csv',
            title='Changes Detected',
            initial_comment="Changes have been detected in your tracked data."
        )

    # Clean up the changes file
    os.remove(changes_filename)

async def daily_refresh_task(app):
    """
    This function runs daily to refresh the data and check for changes.
    """
    # For each user's tracking file, read the search_hash and cached results
    user_files = glob.glob('*_track.csv')
    for csv_filename in user_files:
        # Assuming the filename is '{user_id}_track.csv'
        user_id = csv_filename.split('_')[0]
        try:
            # Read the search_hash and cached results
            cached_search_hash, cached_results = read_results_from_csv(csv_filename)
            # Re-query the API using the search_hash
            new_results = await query_iris_api(IRIS_API_KEY, IRIS_USER, cached_search_hash)
            # Compare the new results with the cached results
            changes = compare_results(cached_results, new_results)
            # Check if there are any changes
            if changes['added'] or changes['removed'] or changes['modified']:
                # Update the cached results
                save_results_to_csv(csv_filename, cached_search_hash, new_results)
                # Send the user a message with the changes
                await send_changes_to_user(app, user_id, changes)
            else:
                # No changes detected
                print(f"No changes detected for user {user_id} and search_hash {cached_search_hash}")
        except Exception as e:
            print(f"Error processing user {user_id}: {e}")

