import paramiko
import os
from datetime import datetime
import concurrent.futures
import time

def execute_subfinder_and_retrieve_output(host):
    port = 22
    username = "ec2-user"
    private_key_path = os.path.join(os.getcwd(), "private_key.pem")

    try:
        print(f"Starting operations on {host}...")

        # Set up the SSH client
        print(f"Connecting to {host} via SSH...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(host, port=port, username=username, key_filename=private_key_path)

        # Fetch list of domains from domains_chunk.txt
        sftp = ssh_client.open_sftp()
        with sftp.file("/home/ec2-user/domains_chunk.txt", "r") as remote_file:
            domains = remote_file.readlines()

        for domain in domains:
            domain = domain.strip()
            print(f"Running subfinder for domain {domain} on {host}...")
            subfinder_cmd = f"""
                cd /home/ec2-user
                subfinder -s dnsdb -t 20 -active -timeout 10 -d {domain} >> subdomains.txt
            """
            stdin, stdout, stderr = ssh_client.exec_command(subfinder_cmd)
            error = stderr.read().decode('utf-8')

            if error:
                print(f"Error occurred while processing {domain} on {host}: {error}")
                time.sleep(10)

        # Retrieve the final output file
        print(f"Retrieving subdomains.txt from {host}...")
        utc_timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        local_filename = f"subdomains_{host}_{utc_timestamp}.txt"
        sftp.get(f"/home/{username}/subdomains.txt", local_filename)
        sftp.close()

        # Close the SSH client
        print(f"Completed operations for {host}. Closing connection...")
        ssh_client.close()

    except Exception as e:
        print(f"Error occurred for {host}: {str(e)}")
        return

# Read IPs from ec2ip.csv
with open('ec2ip.csv', 'r') as f:
    hosts = f.read().splitlines()

# Use ThreadPoolExecutor to execute functions concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
    executor.map(execute_subfinder_and_retrieve_output, hosts)
