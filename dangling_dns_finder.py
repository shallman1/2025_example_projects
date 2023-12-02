import requests
import openpyxl
import tldextract
from datetime import datetime, timedelta
import json

# Constants
API_KEY = 'dnsdb_api_key'
BASE_URL = 'https://api.dnsdb.info/dnsdb/v2/regex/rrnames/'
HEADERS = {
    'X-API-KEY': API_KEY,
    'Accept': 'application/x-ndjson'
}
LIMIT = 40000
SWCLIENT = 'dangling_dns_finder'
VERSION = '0.1'

# Variables to define the time fence in days
time_seen_after_days_all_time = 90
time_seen_before_days_all_time = 0  
time_seen_after_days_last_3_months = 10  
time_seen_before_days_last_3_months = 0  

# Calculate the time_last_after based on the current date and the variables
current_time = datetime.utcnow()
time_last_after_all_time = int((current_time - timedelta(days=time_seen_after_days_all_time)).timestamp())
time_last_after_last_3_months = int((current_time - timedelta(days=time_seen_after_days_last_3_months)).timestamp())

# Function to fetch DNS records with pagination
def fetch_dns_records(term, time_last_after=None):
    qualified_records_set = set()
    disqualified_records_set = set()
    offset = 0
    more_records_available = True

    while more_records_available:
        url = f"{BASE_URL}^.*\\.*{term}.*\\.[^.]*\\..*$/ANY?limit={LIMIT}&offset={offset}&swclient={SWCLIENT}&version={VERSION}"
        if time_last_after is not None:
            url += f"&time_last_after={time_last_after}"

        print(f"Executing query: {url}")  # Print the query being executed
        response = requests.get(url, headers=HEADERS)
        lines = response.text.strip().split("\n")
        batch_records = {json.loads(line)["obj"]["rrname"] for line in lines if "obj" in json.loads(line)}  # Use json.loads instead of eval

        # Filter records using tldextract and separate qualified and disqualified
        for record in batch_records:
            domain = tldextract.extract(record).domain
            # Disqualify records that match the term or contain 'wildcard'
            if domain == term or 'wildcard' in record.lower():
                disqualified_records_set.add(record)
            else:
                qualified_records_set.add(record)

        offset += LIMIT
        more_records_available = len(batch_records) == LIMIT
    
    return list(qualified_records_set), list(disqualified_records_set)


# Term
term = 'domaintools'

# Fetch and filter DNS records
all_time_records, disqualified_all_time = fetch_dns_records(term, time_last_after=time_last_after_all_time)
last_3_months_records, disqualified_last_3_months = fetch_dns_records(term, time_last_after=time_last_after_last_3_months)

# Deduplicate records before finding dangling records
all_time_records = list(set(all_time_records))
last_3_months_records = list(set(last_3_months_records))
disqualified_records = list(set(disqualified_all_time + disqualified_last_3_months))

# Find dangling records
dangling_records = set(all_time_records) - set(last_3_months_records)

# Create Excel workbook and sheets, add records
wb = openpyxl.Workbook()
ws1 = wb.active
ws1.title = f"Records after {time_seen_after_days_all_time} days"
ws2 = wb.create_sheet(title=f"Last {time_seen_after_days_last_3_months} Days Records")
ws3 = wb.create_sheet(title="Dangling Records")
ws4 = wb.create_sheet(title="Disqualified FQDNs") 

for idx, record in enumerate(all_time_records, 1):
    ws1.cell(row=idx, column=1, value=record)

for idx, record in enumerate(last_3_months_records, 1):
    ws2.cell(row=idx, column=1, value=record)

for idx, record in enumerate(dangling_records, 1):
    ws3.cell(row=idx, column=1, value=record)

for idx, record in enumerate(disqualified_records, 1): 
    ws4.cell(row=idx, column=1, value=record)

# Save Workbook
wb.save("dns_records.xlsx")

print("Excel workbook has been created.")
