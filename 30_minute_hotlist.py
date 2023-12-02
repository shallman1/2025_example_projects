import requests
import time
from datetime import date
from elasticsearch import Elasticsearch
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import io

def main(data, context):
    def iris_investigate_api(initial_hashes, fallback_hashes):
        api_key = 'apikey'
        api_username = 'user'
        base_url = 'https://api.domaintools.com/v1/'
        endpoint = 'iris-investigate'

        params = {
            'search_hash': None,
            'app_partner': 'Solutions_Engineering',
            'app_name': 'Hourly_Hot_list',
            'app_version': '1.2',
            'api_username': api_username,
            'api_key': api_key
        }

        results = []

        for hash_set in [initial_hashes, fallback_hashes]:
            for search_hash in hash_set:
                params['search_hash'] = search_hash
                if 'position' in params:  # Reset the position for each hash
                    del params['position']

                try:
                    while True:
                        response = requests.get(f'{base_url}{endpoint}', params=params)
                        data = response.json()

                        # exception handler
                        if response.status_code != 200 or 'results' not in data['response']:
                            print(f"Failed request with status code: {response.status_code}. Retrying with next search hash...")
                            break

                        results.extend(data['response']['results'])

                        if not data['response']['has_more_results']:
                            break

                        params['position'] = data['response']['position']

                except requests.exceptions.RequestException as e:
                    print(f'Request error: {e}')
                    return None


            if results:
                # If any results found in the initial hash set, do not use the fallback hash set.
                break

        return results if results else None

    initial_hashes = ['U2FsdGVkX1/WlKT1u8vfrpb3+u0lss16+9UEhkkPhCmDX7Zkuiib4+OLuLVDFUUI2wQ9xF+CtQfZqQqyKZUkroY5oAiTFac1dmyaREzWE7XeLhxMuB+IqmVwESLKzUPnJURJE0ZFU6X3PEFMUDLpQOssFNDlowVQIbXYnSBD9Ja17Z+o4KlgA1Bw/P5SuNmTDgJeT0xRty90nsxYVEM3V73gKvR8fGjGHZqJomza1yDIDnAlRxSH8RfwmsuoK4G7P95oTVpPtVfaaDdWVbGyUB3s+Id8CpQ7zht2q0u3HAMFHngJnhyzf9VOwo9Uf413e7g28JYHC3+d3KrzPp0ptsvCwryj8vhopdpTkvNZggzk6yfbYgE/szOWNRJeFgQ6ARugD+HMK+rNrH02vhBqS/R0R/dFAZNOU10XlY/pANohEH2gFJbIKQhIhJir5cU3TqkvxC289U3v1xenkDWbsseASZAfOxbpEQFrMOzUMvZZVy51YhxGRetY6gBrkPsfx2TgyBQYjVDzlddt0oae7FjaOQquJ/nbSGlp5W8VCD+8MI8mtIjorJmlERfu4Jd9hpfOMyeIblkETPnCDqmFwaAzTPKPW4DAG7DQ8sGe8JHY8nrEQpL3blHbwLEE5ldh6SIHdkwVzEixM/brOCA9R27d4s2xST8kRbkil0f6uNFO6rx9S57gTbH2HPx187/Sxsn+ridQFfvlnLcXTrMuj+aUDvftkl8EyHTdbq/Cz6RiZEfqWRGfLxBtp1eYSuSjCiQlF/A9ml1tTwQELQYw5/PxkjNpsC/j6EKbUKzRgjtW1lRzNXp2u0UYpegut7NC6QNvPaWwnhgZVvFgHOlx/+jcBqbCEF+2wlM+JqUcT+H+SPV7d8Mn3B04hNRG0FOnrynQVb2nEiI3I5EmIhP9oFnolmq8/1BRX7Ruu6CMH5O5X3U7HhxYYkmZGxkpCRHo6TwhQrNuKw2B0RQcFQI/v6Ce7BXr0692R+Jan2WNip7NLMX1Yb2ZSDj4prrPhsssQOim+DPqxej8vvFSAk9iwSZzuGOGJiFml1eHzY2u0Oz7P0UAJL55v0o4WnLX1DRQP+A8YxooTILclHs/GGbalVSdi9jKUfowLT238mYj890+rkmAly7NsraYKop0oqwgAoDxTBjkcAocGNmTLaeNYWqPC+9H7KfWXTgHjnbb/Rpw+qJUzwMHm5ZCjkbo1EuDukRVwF5s/FHIKOUkals4iZWU+qMHhkMGVpWv/OvRHIqF2vEtYxdaafRuCD3YfElIN1MUQI5Rkoxq5NUoVMqE8PaoKBX0x1hF5m5P5m38HXcqNpXmev121AFomTqmXoj2KIASPidjMKRJ/irUIMc2Ue02kFrcdMM/5ampK1aarPOszhALTnh0u+44LpBp01VCQSR+insnUqs7nZKNziavhoXfHogff77WuudKMvSMY9juG3/zI/7ueOyTUYGsnPxYIYjakaU3cpeWBx3zEwY0x1SHYHw+Tqi4upujszy8BJI=',
                      'U2FsdGVkX191SvRi2CoYwPMS4LBvDI3Tl+/hAzMUs0c+hE+dSbZMh+6VQmavobUOj9R+8FLDUU/jpHR9WOtxdxz5NkT0wPSwDe5ZPhzFgNfAEtZTozEr07NL1ziEeL78okQfxOsQv2g0WoGo+H0fvwh6Kow7aV50fFHIGUKQubZAku3rwjVo2u6wYAHCShZMTciwaQUf8KbyHsxB4BiNQnQbWoCf4WA5ivS7pMLvqsU=']  # Replace with your initial search hashes
    fallback_hashes = ['U2FsdGVkX19DQb/4lcb7DpNuAsk2r02HTaHwarWOjtaaUDmXeoKgvYh7h4EZ1j9Ef4c/uoaOh4THwsvSk46wZ2XcVxtWcA72+U3Pva0wCsNHz0kqbUNx7JN/TQOnOvX5ztG9Ql7Hbh8ZJhgQOxxe0S1aMV7HU42p+VSGKN2hRE9pfKrdD/n47jcTcVix/F4YN3LxMRVVAFHjPQTCzdPOEJ+zPche+LWCZFEH/Tw86hw7XQRZ4xY4+Dte/dGyVmr+zap+aDW6tv6ij+qbN0cnJg==', 
                       'U2FsdGVkX19cFCx3Zv7HAIGNdW9Bgt/dTpMhoseFNi/NxyOIjfnv1SU1XW3joC+rsPNTqDAjSr4Ec3RMo/hxrY6rUXRf7bixT2D0/Oonx+9XeRuETPINXef4L6t9j+yGoZi60zulbJtfz4GTLWjL8gWrEshnF7scS8Oi4Ti5sX7Qj6neKrH29E2xdr6L92v/2bCkHaC28MD67zfx2sxtWnULRdLPKdDyFS3J4SK+yJctPeGwChLmH1yOxyl+KijcV4BCHUIyNfbz7EjTlwB6CA==', 
                       'U2FsdGVkX1+XHXK1KBm+/KMcOnNpMF9jBhx3yLSfx9ZUIOg+u94GdyeZFZB0AUg7mntgoNq+PqsXFj91teJcZ0NE7yfSTe3dM6Vcmjtadh/d+DfOkmHi/obMu+KZlxK+a5D8k3zkxvUAmNugSyOKwwKkiBQx5HKDVvmD+dRrV+Xrle3Ycw9NllYFmIWxmcSeVbpX6aa1y7InJO0zHPhOsDrXX1MU76QoAeh9TrNMkzqB4xbm6jvnyNo2wVuTSnVec2J248YN1yPJb4iWLqKhgKdm52EyQfmk05BuQZhuQDStT4mKr61Yzi7BpM0/lWO2HyQl8H+vr+BmtfaYrtr9E2c21N+X5dJUhtSIlYpi3+hfNhIhgPqyTEbQV3jkPYVEvYDUt8XmlLEpS757Sd0H3LmVtd+fPbK95G0l1TUztA2okOSNpthDogM7TGfXZEFlgNJ+vbP1+AJFB/Wk/PtkGwS8FaFbTTa/2gKTESM/4iZCfBf+sx+xOo6iMsX5dIoBEdAhVkkqJAFRQmGDsmlz/zAtld/7iNM1oGewd8AXEBwyc6hEPaVyc3nn1rtdqmympwAInZHM46QSu43SKkr4+cEqwxGpLHCSfyFMyivDejI61pkphpc+qtrXh15p9iqYIdVl2Fs/LsyahANPAAZkunrUitiiMDHPatNyRLdTsIf6SBG6eaIEL1UodqgOpzwoGrkb771AsUQox6JAT/EoUBpVEwMWrbTT/rywBFmIiQ1iOW/n4kgFa8/yfhSApltw10PmUzU5sLUCIuEpxAB4/Qrajphw/mfuZ2lItdQ04foRCbg5qRDhnH0gdwvO07poX9b3c/AH4vVX2beOFIR3tpI1VCKWHsvegvG9zjlhhAEKRTUbLcPrM84z75kajo1byGkP9XqUZZajVTPEKccdwxWLlh0gkiOtta7xykWptdueC2pSJI3sXwqzMLhGU928CyrZIcPHFq5xiVcN0F3HMUKz6JINFhSB8Jv4QaKM8XYA6gShTPzKppRjq3LXvb9sJtpgrVoWsYoNqcSYjkEcer3tW/E5cG8eHH7HsFFmPTcQ8KB5pvQ5YCkkxX2DSfLHdF8Q9ZuU/MPZIVDOq7sOPkFRpON+pk2zCzuDlxPdMz8u5qoOfRSwDFr61MVMX30y3wZOPWj5SCqTMnwzxUC8waMkTTi5R+ZL5bi8kCOP+Z0jEjrTXczWR/8xAMmjUkOpkXSjI0RDahbK1baCJJBMtA/FH1xZ4Vpf4M9UH5D5/BHorlBiKfhVDQWhYptYA5bDd7xRGcYfhIh404xzP3N/q/2bMzPZEmSK8OP22AsGK5cQ8SfpGIaoDNmGO8gdu+V64/s7nehPN4qk0wu38gOFnNlHxznH3nUVk7xIBRtEr+eZqhHfahQtboglZKSNuxNLEkCFD5iaPlujrcUN1CW0s2mLJo9aV9t5rQG+hjM8AUBtV2nquk3PoWinJRut4tkTJ2T24sqKJqyqd9qrT6KOizVrW3tM/uZZkd/PGOXwdmHdqA4mRZtZPnql6sWSeiAU',
                       'U2FsdGVkX1/kFBtjHTvtSrtmkz+y4vIaeUFl523d/28W+0BiXPX59xK1QQP12MgHaK2G+4btkFBSeUoKuUCItnovtsZuEsFTrGEM1gfcGFTCHkrP5Tw5lyUjah7oa3VQRysRiYHqgMiNGiMLQT0Ji3i2jYQDMWQp3/SyJnPk2Jv1unl3PrhpqRwqxzK9/MQ21+b3oH/v+QWb9WwabpeQDtxSUfSWyebx72nriXeM93tFGKo5Ev7/Ganvy5XiNB3II7m4CouT3fUqIsoY2jtdwQ==']  # Replace with your fallback search hashes
    results = iris_investigate_api(initial_hashes, fallback_hashes)
    if results:
        # Elastic config
        es = Elasticsearch(
            cloud_id='DT_Elastic',
            basic_auth=('username', 'password')
        )
        index_name = 'inv_hot'

        # Elastic shipper
        for result in results:
            # Does domain already exist in ES?
            query = {"query": {"term": {"domain": result['domain']}}}
            search_result = es.search(index=index_name, body=query)

            # No? Then Index
            if not search_result['hits']['hits']:
                registrar_email = result['soa_email'][0]['value'] if result['soa_email'] else None  # Parsing soa_email field
                name_servers = [ns['host']['value'] for ns in result['name_server']] if result.get('name_server') else []
                
                document = {
                    'domain': result['domain'],
                    'risk_score': result['domain_risk']['risk_score'],
                    'first_seen': result['first_seen']['value'],
                    'visit_rank': result['popularity_rank'],
                    'registrar_email': registrar_email,
                    'name_server': name_servers,
                    'pulled': 'no'
                }
                es.index(index=index_name, body=document)
            else:
                print(f"Domain {result['domain']} already exists in Elasticsearch, skipping upload.")

        print('Documents sent to Elasticsearch')
    else:
        print('No result or an error occurred.')

    time.sleep(3)    

    def append_to_rpz(documents, drive_service):
            # Google Drive folder ID where the rpz files will be stored
            folder_id = '1iVO1nYbcpMynXCBIBZRbmFDoV1QSeh3U'

            # Create the file name with the current day's date
            today = date.today().strftime('%Y-%m-%d')
            filename = f'hotlist_{today}.rpz'

            # Check if the file already exists
            existing_files = drive_service.files().list(q=f"mimeType='text/plain' and name='{filename}' and '{folder_id}' in parents",
                                                        fields='files(id)').execute()
            files_list = existing_files.get('files', [])
            file_id = files_list[0]['id'] if files_list else None

            # RPZ generation
            rpz_content = ''
            for doc in documents:
                if doc.get('visit_rank', float('inf')) >= 100000:  # If visit_rank is less than 100000, skip this domain
                    domain = doc['domain']
                    rpz_content += f'{domain} CNAME . ; Block\n'

            if file_id:
                # File already exists, append to it
                existing_file = drive_service.files().get_media(fileId=file_id).execute()
                existing_content = existing_file.decode('utf-8')

                # Convert existing_content to a set (deduping in the process)
                existing_lines = set(existing_content.split('\n'))

                # Convert new rpz_content to a set (deduping in the process)
                new_lines = set(rpz_content.split('\n'))

                # Merge old and new sets
                all_lines = existing_lines.union(new_lines)

                # Convert back to string
                new_content = '\n'.join(all_lines)

                # RPZ Uploader
                media = MediaIoBaseUpload(io.BytesIO(new_content.encode('utf-8')), mimetype='text/plain', resumable=True)
                drive_service.files().update(fileId=file_id, media_body=media).execute()

                print("Existing RPZ file in Google Drive appended with new content and deduped")
            else:
                # File does not exist, create new file
                media = MediaIoBaseUpload(io.BytesIO(rpz_content.encode('utf-8')), mimetype='text/plain', resumable=True)
                file_metadata = {
                    'name': filename,
                    'parents': [folder_id]
                }
                drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

                print("New RPZ file created in Google Drive with today's date")


    def update_documents(es, documents):
        # get document IDs
        doc_ids = [doc['_id'] for doc in documents]

        # Update the documents using _update API
        for doc_id in doc_ids:
            es.update(
                index='inv_hot',
                id=doc_id,
                doc={'pulled': 'yes'},
                doc_as_upsert=True
            )

        print("Documents updated with 'pulled' field")

    def query_elastic_cloud():
        # Elastic config
        elastic_cloud_id = "DT_Elastic:"
        username = "username"
        password = "password"

        # Create Elasticsearch client
        es = Elasticsearch(
            cloud_id=elastic_cloud_id,
            basic_auth=(username, password)
        )

        # Query the "hot_nod" index to fetch documents with pulled='no'
        query = {"query": {"term": {"pulled": "no"}}}
        result = es.search(
            index="inv_hot",
            body=query,
            size=10000,  # Adjust the size as per your data volume
            _source=["domain", "risk_score"]
        )

        # Extract the domain and risk_score values from the search results
        documents = []
        for hit in result['hits']['hits']:
            doc_id = hit['_id']
            domain = hit['_source']['domain']
            risk_score = hit['_source']['risk_score']
            documents.append({'_id': doc_id, 'domain': domain, 'risk_score': risk_score})

        return es, documents


    # Query Elasticsearch and retrieve documents
    es, documents = query_elastic_cloud()

    # Authenticate with Google Drive
    credentials = service_account.Credentials.from_service_account_file('credentials.json')
    drive_service = build('drive', 'v3', credentials=credentials)

    # Export documents to CSV file in Google Drive
    append_to_rpz(documents, drive_service)

    # Update documents with 'pulled' field
    update_documents(es, documents)

    print("All Operations Completed")

if __name__ == '__main__':
    main(None, None)
