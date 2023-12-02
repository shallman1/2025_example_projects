from elasticsearch import Elasticsearch, helpers
import csv

# Initialize the Elasticsearch client
# Elasticsearch credentials
elastic_cloud_id = "cloud"
username = "elastic_user"
password = "elastic_password"

# Connect to Elastic Cloud
es = Elasticsearch(
    cloud_id=elastic_cloud_id,
    http_auth=(username, password)
)

# Check if index exists and create if it doesn't
if not es.indices.exists(index='tld_parsed'):  # Change here
    es.indices.create(index='tld_parsed')  # Change here

# Read CSV file
with open('C:\DomainTools Python\Last Mile Scripts\dissected_domains.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Skip the header
    data = [{'tld': row[0]} for row in reader]

# Generate Elasticsearch actions
actions = [
    {
        '_op_type': 'index',
        '_index': 'tld_parsed',
        '_source': item,
    }
    for item in data
]

# Bulk index the data
helpers.bulk(es, actions)

