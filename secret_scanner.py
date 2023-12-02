import os
import subprocess
import sys

def scan_directory_for_secrets(directory):
    """
    Scans the specified directory for secrets using detect-secrets.

    :param directory: The directory to scan.
    """
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        sys.exit(1)

    try:
        # Running the detect-secrets scan command
        result = subprocess.run(['detect-secrets', 'scan', directory], capture_output=True, text=True, check=True)

        # Output the results
        print("Scan Results:")
        print(result.stdout)

    except subprocess.CalledProcessError as e:
        print("An error occurred while scanning for secrets:")
        print(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Hardcoded directory path
    directory_to_scan = 'C:\\example\\example_projects'
    scan_directory_for_secrets(directory_to_scan)


