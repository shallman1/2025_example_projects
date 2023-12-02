import openai
import subprocess
import json

# Initialize OpenAI API
openai.api_key = "openai_key"

def ask_question(question):
    # Prepare the API call payload
    payload = {
        "model": "ft:gpt-3.5-turbo-0613:personal::8ENGhIe4",
        "messages": [
            {
                "role": "system",
                "content": "You're a DNS Assistant named Iris, specialized in converting DNS-related questions into Elasticsearch curl commands.Your\
                            primary task is to generate curl commands formatted specifically for Elasticsearch, adhering strictly to the user's query. \
                            Make sure to use the appropriate _count or _search API based on the question. Limit the fields in the response to 'domain', \
                            'first_seen.value', and 'domain_risk.risk_score', and cap the results at 20 documents. The curl endpoint to use is \
                            https://dt-elastic.es.us-central1.gcp.cloud.es.io/se_engine_*. The headers for the curl command are: -u elastic:lkrgllG4E1F12Qk1KA5uRJzr -H \
                            'Content-Type: application/json'. Provide only the curl command without any additional explanations. For query creation, be aware of the following field names:\
                                - domain.risk_risk.score\
                                - first_seen.value\
                                - website_response\
                                - website_title\
                                - ip1.address.value.keyword (enumerates from 1-5)\
                                - tld\
                                - admin_contact.country.value.keyword (registration country codes)\
                                - name_server1.domain.value.keyword (enumerates from 1-5)\
                                - ip1.country_code.value.keyword (enumerates from 1-5) (Hosting IP Country Code)\
                                - mx1.domain.value.keyword (enumerates from 1-5) (mail server host)\
                                - mx1.ip1.value.keyword (enumerates from 1-5 on both mx and ip) (mail server hosting IP)"
            },
            {
                "role": "user",
                "content": question
            }
        ]
    }

    # Make the API call
    response = openai.ChatCompletion.create(**payload)

    # Extract the curl command from the response
    curl_command = response['choices'][0]['message']['content']

    # Print the curl command for debugging
    print(f"Executing curl command: {curl_command}")

    # Check if the curl command uses the _count endpoint
    is_count_query = "_count" in curl_command

    # Execute the curl command
    process = subprocess.Popen(curl_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    # Print the raw response for debugging
    print(f"Raw Response: {stdout.decode('utf-8')}")

    if process.returncode != 0:
        print(f"Error executing curl: {stderr.decode('utf-8')}")
        return

    # Parse the JSON response
    try:
        response_json = json.loads(stdout.decode('utf-8'))
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return

    # If it's a count query, just print the count
    if is_count_query:
        count_value = response_json.get('count', 'N/A')
        print(f"There are {count_value} domains that match your query.")
        return

# Check if the response contains 'hits' with actual data
    if 'hits' in response_json and 'hits' in response_json['hits'] and response_json['hits']['hits']:
        print("Are these the domains you're looking for?")
        for hit in response_json['hits']['hits']:
            first_seen_value = hit['_source'].get('first_seen.value', 'N/A')
            domain = hit['_source'].get('domain', 'N/A')
            risk_score = hit['_source'].get('domain_risk.risk_score', 'N/A')
            
            print(f"First Seen: {first_seen_value}, Domain: {domain}, Risk Score: {risk_score}")

    # Check if the response contains only a 'value' count
    elif 'hits' in response_json and 'total' in response_json['hits'] and 'value' in response_json['hits']['total']:
        count_value = response_json['hits']['total']['value']
        print(f"There are {count_value} domains that match your query.")

    else:
        print("Unexpected response format.")

if __name__ == "__main__":
    # Get user input
    user_question = input("Please enter your DNS-related question: ")
    
    # Call the function to ask the question and get the Elasticsearch query
    ask_question(user_question)
