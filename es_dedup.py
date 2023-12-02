from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan

# Connect to Elastic Cloud
elastic_cloud_id = "cloud"
username = "username"
password = "password"
index_name = "inv_hot"

# Create Elasticsearch client
es = Elasticsearch(
    cloud_id=elastic_cloud_id,
    basic_auth=(username, password)
)

# Query to fetch all documents
query = {
    "query": {
        "match_all": {}
    }
}

# Scroll through all documents
documents = []
for doc in scan(es, index=index_name, query=query):
    documents.append(doc)

# Group documents by 'domain'
domains = {}
for doc in documents:
    domain = doc["_source"]["domain"]
    if domain not in domains:
        domains[domain] = []
    domains[domain].append(doc)

# Prepare documents for deletion
docs_to_delete = []
for domain, docs in domains.items():
    if len(docs) > 1:
        # Find the document(s) with the least amount of content
        min_fields = float("inf")
        docs_with_min_fields = []
        for doc in docs:
            num_fields = len(doc["_source"])
            if num_fields < min_fields:
                min_fields = num_fields
                docs_with_min_fields = [doc]
            elif num_fields == min_fields:
                docs_with_min_fields.append(doc)

        # Keep one document with the minimum fields
        docs_to_delete.extend(docs_with_min_fields[:-1])

# Delete duplicate documents
actions = [{"_op_type": "delete", "_index": doc["_index"], "_id": doc["_id"]} for doc in docs_to_delete]
success, _ = bulk(es, actions)

print(f"Deleted {success} duplicate documents.")


