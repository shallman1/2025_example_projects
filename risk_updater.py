from elasticsearch import Elasticsearch, helpers
import requests
import time

# Iris Creds
API_USERNAME = 'username'
API_KEY = 'apikey'
API_URL = 'https://api.domaintools.com/v1/iris-enrich/'

# Elasticsearch config
es = Elasticsearch(
    cloud_id='DT_Elastic',
    basic_auth=('username', 'password')
)

# Search query for Elasticsearch
body = {
    "_source": ["domain", "risk_score"],
    "query": {
        "match_all": {}
    }
}

# helper function
res = helpers.scan(es, query=body, index='inv_hot')

# Extract values
domains_risks = [(hit['_id'], hit['_source']['domain'], hit['_source']['risk_score']) for hit in res]

# batch
batch_size = 100

# Process Batch
def process_batch(domains_risks):
    domains_str = ','.join(domain for _, domain, _ in domains_risks)

    
    response = requests.get(
        API_URL,
        params={
            'domain': domains_str,
            'app_partner': 'Solutions_Engineering',
            'app_name': 'elastic_risk_updater',
            'app_version': 1.0,
            'api_username': API_USERNAME,
            'api_key': API_KEY
        }
    )

    
    if response.status_code == 200:
        data = response.json()

        
        for result in data['response']['results']:
            for id, domain, old_risk_score in domains_risks:
                if domain == result['domain']:
                    new_risk_score = result['domain_risk']['risk_score']

                   
                    if new_risk_score != old_risk_score:
                        es.update(
                            index='inv_hot',
                            id=id,
                            body={
                                'doc': {
                                    'updated_risk_score': new_risk_score
                                }
                            }
                        )

    return response.status_code

# Process domains in batches
for i in range(0, len(domains_risks), batch_size):
    batch_domains_risks = domains_risks[i:i+batch_size]
    
    # 414 handler
    if process_batch(batch_domains_risks) == 414:
        half = len(batch_domains_risks) // 2
        process_batch(batch_domains_risks[:half])
        process_batch(batch_domains_risks[half:])

    # sleep for rate limiting
    time.sleep(1)
