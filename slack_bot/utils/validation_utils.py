# utils/validation_utils.py

import re
from urllib.parse import urlparse

def is_valid_ip(address):
    ipv4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if ipv4_pattern.match(address):
        parts = address.split('.')
        if all(0 <= int(part) <= 255 for part in parts):
            return True
    return False

def is_valid_domain(domain):
    # Remove any trailing dot
    domain = domain.rstrip('.')
    if len(domain) > 253:
        return False
    labels = domain.split('.')
    allowed = re.compile(r'^[a-zA-Z0-9_-]{1,63}$')
    for label in labels:
        if not allowed.match(label):
            return False
    return True

def is_valid_url(url):
    """Validate if the given string is a valid URL."""
    try:
        # Add https:// prefix if not present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        result = urlparse(url)
        # Check if scheme and netloc are present
        return all([result.scheme, result.netloc])
    except:
        return False
