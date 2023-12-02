import csv
import json
from typing import List
import requests
import datetime
import time

#This parses the last 5 minutes from nod on a 60 minute delay, and enriches the domains with the Enrich API if the risk score is => 70, giving risk score and the date populated is the time it was enriched. It also creates another csv with a list of domains that could not be found in the Enrich API.

class NDJSONParser:
    def __init__(self, data: str):
        self.data = data

    def parse_domains(self) -> List[str]:
        domains = []
        lines = self.data.split("\n")
        for line in lines:
            if line:  # Check if line is not empty
                data = json.loads(line)
                domain = data['message']['domain']
                domain = domain.rstrip('.')  # Remove trailing periods
                domains.append(domain)
        return domains
    
def fetch_data():
    # URL for the API endpoint
    url = "https://batch.sie-remote.net/siebatchd/v1/siebatch/chfetch"

    # Get the current time, offset by 60 minutes
    current_time = datetime.datetime.now() - datetime.timedelta(minutes=60)

    # Set end_time to the offset current time, formatted as a string
    end_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    # Set start_time to 5 minutes before end_time, formatted as a string
    start_time = (current_time - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")

    # Data payload for the API request
    data = {
        "apikey": "dnsdb_api",
        "channel": 212,
        "start_time": start_time,
        "end_time": end_time
    }

    retry_count = 0
    while retry_count < 3:
        # Send a POST request to the API
        response = requests.post(url, json=data)

        # Check if the request was successful
        if response.status_code == 200:
            return response.text
        elif response.status_code == 503:
            retry_count += 1
            print(f"Retrying request... Attempt {retry_count}")
            time.sleep(5)
        else:
            print(f"Failed to fetch data, status code: {response.status_code}")
            return None

    print("Exceeded maximum retry attempts.")
    return None

def process_portion(domains, results, missing_domains, api_username, api_key):
    domain_item = ','.join(domains)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')  # CSV-friendly format

    while True:
        response = requests.get(f'https://api.domaintools.com/v1/iris-enrich/?domain={domain_item}&api_username={api_username}&api_key={api_key}')

        if response.status_code == 200:
            data = response.json()

            for result in data['response']['results']:
                domain = result['domain']
                risk_score = result['domain_risk']['risk_score']

                if risk_score is not None and risk_score >= 70:
                    results.append([domain, risk_score, timestamp])

            for missing_domain in data['response']['missing_domains']:
                if missing_domain not in missing_domains:  # Deduplicate missing domains
                    missing_domains.append(missing_domain)

            break

        elif response.status_code == 503:
            print("API temporarily unavailable. Retrying request...")
            time.sleep(5)

        elif response.status_code == 403:
            print("Access forbidden. Skipping request...")
            break

        elif response.status_code == 414:
            midpoint = len(domains) // 2
            process_portion(domains[:midpoint], results, missing_domains, api_username, api_key)
            process_portion(domains[midpoint:], results, missing_domains, api_username, api_key)
            break

        else:
            print(f"Request failed with status code {response.status_code}")
            break

def process_domains(domains, api_username, api_key):
    portions = [domains[i:i + 100] for i in range(0, len(domains), 100)]
    results = []
    missing_domains = []

    for portion in portions:
        process_portion(portion, results, missing_domains, api_username, api_key)

    return results, missing_domains

def write_to_csv(data, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)

def main(event, context):
    api_username = 'username'
    api_key = 'apikey'

    # Run the fetch_data() function
    response_text = fetch_data()

    if response_text is not None:
        # Delay between the two scripts
        time.sleep(10)

        parser = NDJSONParser(response_text)
        domains = parser.parse_domains()

        print("Domains parsed and handled internally")

        # Process the domains
        results, missing_domains = process_domains(domains, api_username, api_key)

        # Save results to CSV
        write_to_csv(results, 'results.csv')
        write_to_csv([[d] for d in missing_domains], 'missing_domains.csv')

        print("Data saved to CSV files")

# Trigger the main function
main(None, None)








