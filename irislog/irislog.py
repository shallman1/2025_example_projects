import requests
from datetime import datetime
import uuid
from elasticsearch import Elasticsearch, helpers
from log_templates import *

# API Configuration
API_ENDPOINT = "https://api.domaintools.com/v1/iris-investigate"
SEARCH_HASH = "U2FsdGVkX197qARbv/uPrOgu3sVPEWnFKMTlVAkWb//LZ0GAFmdWB8ZJB2khEaR5pOqtwjuP7N7mypfOSRY9jlYFc8y6j4Khfu/HgZ6KNYatSj4XjNUrNDX/fOjBmDFS89157q2T6Mc1Sw/dVUDO53aP/zmelPllUsvUp80edbekKri4LU++tYozC5x8jXvhL8ypZ+bQS0Yi++bKJKMAQSFlr48Dic52WrT/SjLgEosA6eQT0lRtRRq4ziX2nSxd8r2tMw8mX8AUvrxAfjyWSPdaqyjxv2bacfbLebQvImY2HQyAiO3J5qHWGbf1na3e"  # Replace with your search_hash
API_USERNAME = 'dt_user'  
API_KEY = 'dt_api' 

class DomainToolsAPI:
    def __init__(self, api_key, api_username, search_hash):
        self.api_key = api_key
        self.api_username = api_username
        self.search_hash = search_hash

    def get_domain_details(self):
        params = {
            "search_hash": self.search_hash,
            "api_username": self.api_username,
            "api_key": self.api_key
        }
        
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        return response.json()['response']['results']
        

# SIEM CONFIGURATION
SIEM_CONFIGS = {
    "Splunk": {
        "endpoint": "splunk_cloud",
        "token": "splunk_token",
        "headers": {
            "Authorization": lambda config: f"Splunk {config['token']}",
            "X-Splunk-Request-Channel": lambda _: str(uuid.uuid4())
        }
    },
    #"ElasticCloud": {
    #    "cloud_id": "example",
    #    "auth": ('user', 'password'),
    #}
}
#This is only for Elastic endpoints.
LOG_TEMPLATE_PIPELINE_MAPPING = {
    "PaloAltoFirewallLogTemplate": "firewall_pipeline",
    "MicrosoftExchangeLogTemplate": "exchange_log_parser",
    "WindowsDnsLogTemplate":"dns_log_parser"
    # As more log templates are added, add them here.
    # "AnotherLogTemplate": "another_pipeline",
    # ...
}    
class SIEMIntegration:
    SPLUNK_BATCH_SIZE = 100
    ELASTIC_BATCH_SIZE = 100

    def send_to_siem(self, logs, siem_name, log_template_name=None):
        siem_config = SIEM_CONFIGS.get(siem_name)
        if not siem_config:
            print(f"No configuration found for SIEM: {siem_name}")
            return

        if siem_name == "Splunk":
            headers = {
                key: func(siem_config) for key, func in siem_config['headers'].items()
            }

            # Send logs to Splunk in batches
            for i in range(0, len(logs), self.SPLUNK_BATCH_SIZE):
                batched_logs = logs[i: i + self.SPLUNK_BATCH_SIZE]
                data = [
                    {"event": log, "sourcetype": log_template_name} for log in batched_logs
                ]
                response = requests.post(siem_config['endpoint'], headers=headers, json=data, verify=False)
                if response.status_code != 200:
                    print(f"Failed to send log batch to {siem_name}. Status code: {response.status_code}, Response: {response.text}")
        
        elif siem_name == "ElasticCloud":
            es = Elasticsearch(
                cloud_id=siem_config['cloud_id'],
                basic_auth=siem_config['auth'],
                request_timeout=siem_config['timeout']
            )
            index_name = "irislog"

            # Prepare logs for Elasticsearch Bulk API
            actions = [{"_index": index_name, "_source": {"message": log}} for log in logs]

            # If the log template name is provided and it has an associated pipeline, add it
            if log_template_name and log_template_name in LOG_TEMPLATE_PIPELINE_MAPPING:
                pipeline_name = LOG_TEMPLATE_PIPELINE_MAPPING[log_template_name]
                for action in actions:
                    action["pipeline"] = pipeline_name

            # Use the helpers module's bulk function to index the list of actions
            try:
                success, failed = helpers.bulk(es, actions)
                if failed:
                    print(f"{len(failed)} operations failed.")
                    for item in failed:
                        # Print more details about each failed item
                        print(item['index']['_id'], item['index']['status'], item['index']['error']['type'], item['index']['error']['reason'])
            except Exception as e:
                print(f"Error while sending log batch to {siem_name}: {e}")

class LogTemplatesManager:
    @staticmethod
    def get_all_templates():
        # Add all the templates to this list.
        return [PaloAltoFirewallLogTemplate, MicrosoftExchangeLogTemplate,WindowsDnsLogTemplate, PaloAltoCortexXDR, ProofPoint_email_log]

def split_domain_objects_among_templates(domain_details, templates):
    split_domains = {}
    for i, domain in enumerate(domain_details):
        # Assign each domain to a template in a round-robin fashion
        template = templates[i % len(templates)]
        if template not in split_domains:
            split_domains[template] = []
        split_domains[template].append(domain)
    return split_domains


def main():
    try:
        api = DomainToolsAPI(API_KEY, API_USERNAME, SEARCH_HASH)
        siem_integration = SIEMIntegration()

        domain_details = api.get_domain_details()
        
        # Split domain details among all log templates
        all_templates = LogTemplatesManager.get_all_templates()
        domain_splits = split_domain_objects_among_templates(domain_details, all_templates)
        
        # Generate and send logs for each template
        for template_class, domains in domain_splits.items():
            log_template = template_class()
            logs = log_template.generate_logs({"response": {"results": domains}})
            for siem_name in SIEM_CONFIGS.keys():
                siem_integration.send_to_siem(logs, siem_name, log_template_name=log_template.__class__.__name__)

    except requests.RequestException as re:
        print(f"Request Error: {re}")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
