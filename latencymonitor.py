from icmplib import ping
import csv
import datetime
import time
import os

# Function to get the current timestamp
def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Function to perform a ping and return the metrics using icmplib
def perform_ping(host, count=4):
    # Send ping requests to the host
    try:
        response = ping(host, count=count, interval=0.25)
        return {
            'latency': response.avg_rtt,
            'packet_loss': response.packet_loss,
            'jitter': response.jitter,
        }
    except PermissionError:
        raise PermissionError("You need to run this script with administrative privileges to perform raw socket operations.")

# Function to write the metrics to a CSV file
def write_to_csv(metrics, file_path, header=False):
    with open(file_path, mode='a', newline='') as csvfile:
        fieldnames = ['timestamp', 'latency', 'packet_loss', 'jitter']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if header:  # Write the header if needed
            writer.writeheader()

        writer.writerow(metrics)

# Main monitoring function
def monitor_connection(file_path, host, interval=1):
    try:
        # Check if the CSV needs a header
        header_needed = not os.path.exists(file_path)

        # Main loop to monitor the connection
        while True:
            # Get current metrics
            metrics = perform_ping(host)
            metrics['timestamp'] = get_timestamp()

            # Write the metrics to the CSV
            write_to_csv(metrics, file_path, header=header_needed)

            # Reset header flag after first write
            header_needed = False

            # Wait for the specified interval before the next check
            time.sleep(interval)

    except KeyboardInterrupt:
        print("Monitoring stopped by user.")

# Set parameters and start monitoring
host_to_ping = '8.8.4.4'
file_path_to_log = 'C:\filepath\internet_connection_log.csv'

# Start the monitoring process (will run until manually stopped)
monitor_connection(file_path_to_log, host_to_ping)

if __name__ == "__main__":
    metrics = perform_ping(host_to_ping)
    metrics['timestamp'] = get_timestamp()
    write_to_csv(metrics, file_path_to_log, header=True)

    print(f"Logged metrics to {file_path_to_log}")
    print(metrics)
