# Cybersecurity Slack Bot User Guide

## Introduction

The Cybersecurity Slack Bot provides a suite of commands for performing various cybersecurity analysis tasks directly in Slack. This guide explains how to use each command, with examples and expected outputs.

## Command Reference

### 1. `/dns_history` - DNS History Analysis

**Description:**  
Analyzes the DNS history of domains and IP addresses to find overlapping relationships.

**Syntax:**  
```
/dns_history <domain_or_ip1>,<domain_or_ip2>,...
```

**Parameters:**
- `domain_or_ip`: A comma-separated list of domains or IP addresses to analyze

**Example:**
```
/dns_history example.com,suspicious-domain.com,192.168.1.1
```

**Expected Output:**
```
Overlapping IP addresses found:
- 203.0.113.1 shared among: example.com, suspicious-domain.com

Overlapping hostnames found:
- shared-server.host.com shared among: example.com, 192.168.1.1
```

**Use Case:**  
This command helps identify relationships between different domains and IP addresses through their DNS history, which is useful for threat hunting and investigating potential infrastructure connections among suspicious entities.

---

### 2. `/fingerprint` - Analysis Report Generation

**Description:**  
Generates a detailed analysis report based on a search hash from Iris Investigate.

**Syntax:**  
```
/fingerprint [-limit <percentage>] [-empty] <search_hash>
```

**Parameters:**
- `search_hash`: The Iris Investigate search hash to analyze
- `-limit <percentage>` (Optional): Correlation limit percentage (default: 10%)
- `-empty` (Optional): Include empty fields in the analysis

**Example:**
```
/fingerprint -limit 15 -empty a1b2c3d4e5f6g7h8i9j0
```

**Expected Output:**  
The command will generate and upload a Word document (DOCX) with a detailed analysis report based on the specified search hash, showing correlations at the specified limit threshold.

**Use Case:**  
Use this command to generate comprehensive reports from Iris Investigate findings, allowing for detailed analysis of security incidents or threats with configurable correlation thresholds.

---

### 3. `/subdomains` - Subdomain Discovery

**Description:**  
Discovers and lists subdomains for specified domains using DNSDB data.

**Syntax:**  
```
/subdomains <domain1,domain2,...>
```

**Parameters:**
- `domain`: A comma-separated list of domains to find subdomains for

**Example:**
```
/subdomains example.com
```

**Expected Output:**
```
Subdomain Report (Page 1/5)
 example.com
|- api.example.com
|- mail.example.com
|- dev.example.com
|- test.example.com
|- stage.example.com
|- beta.example.com
|- secure.example.com
|- cdn.example.com
|- admin.example.com
|- support.example.com
|- blog.example.com
|- shop.example.com
|- mobile.example.com
|- login.example.com
|- www.example.com
```

The output includes pagination buttons for navigating through the results if there are many subdomains.

**Use Case:**  
This command helps identify the attack surface of a domain by discovering all related subdomains, which is useful for both defensive security assessments and offensive security testing.

---

### 4. `/supplychain` - Supply Chain Analysis

**Description:**  
Analyzes subdomains for brand mentions to identify potential supply chain relationships.

**Syntax:**  
```
/supplychain <domain1,domain2,...>
```

**Parameters:**
- `domain`: A comma-separated list of domains to analyze for brand mentions

**Example:**
```
/supplychain example.com
```

**Expected Output:**
```
Supply Chain Analysis Results:
- amazon found in cdn-amazon.example.com (last seen: 2023-05-15 14:20:33 UTC)
- cloudflare found in cloudflare-cdn.example.com (last seen: 2023-06-22 09:12:45 UTC)
- microsoft found in login-microsoft.example.com (last seen: 2023-04-30 18:05:27 UTC)
```

**Use Case:**  
Use this command to identify third-party services and vendors a domain might be integrated with, helping to map potential supply chain vulnerabilities.

---

### 5. `/track` - Search Hash Tracking

**Description:**  
Tracks changes for a specific Iris Investigate search hash over time.

**Syntax:**  
```
/track <search_hash>
```

**Parameters:**
- `search_hash`: The Iris Investigate search hash to track

**Example:**
```
/track a1b2c3d4e5f6g7h8i9j0
```

**Expected Output:**
```
Tracking started for search_hash `a1b2c3d4e5f6g7h8i9j0`. You will be notified of any changes.
```

The system will save the current state and notify you of any changes to the search hash results over time.

**Use Case:**  
This command is useful for continuous monitoring of specific indicators or threats, automatically alerting you to any changes in the data associated with the search hash.

---

### 6. `/mx_security` - Email Security Analysis

**Description:**  
Analyzes a domain's email security records (SPF, DKIM, DMARC).

**Syntax:**  
```
/mx_security <domain>
```

**Parameters:**
- `domain`: The domain to analyze

**Example:**
```
/mx_security example.com
```

**Expected Output:**
```
SPF, DKIM, and DMARC Records for example.com:

SPF Records:
Record Name: `example.com`
- First Seen: 2023-01-15 08:30:22 UTC
  Last Seen: 2023-06-22 14:45:33 UTC
  Record Details:
    - v=spf1
    - include:_spf.google.com
    - include:spf.protection.outlook.com
    - ip4:203.0.113.1
    - ~all

DMARC Records:
Record Name: `_dmarc.example.com`
- First Seen: 2023-02-10 11:20:15 UTC
  Last Seen: 2023-06-22 14:45:33 UTC
  Record Details:
    - *v*: DMARC1
    - *p*: reject
    - *sp*: reject
    - *pct*: 100
    - *rua*: mailto:dmarc-reports@example.com

DKIM Records:
Record Name: `selector1._domainkey.example.com`
- First Seen: 2023-02-10 11:22:33 UTC
  Last Seen: 2023-06-22 14:45:33 UTC
  Record Details:
    - *v*: DKIM1
    - *k*: rsa
    - *p*: MIIBIjANBgkqhkiG9w0BAQEFAAOC...
```

**Use Case:**  
This command helps assess a domain's email security posture, identifying potential vulnerabilities in email authentication mechanisms that could lead to spoofing or phishing attacks.

---

### 7. `/dga` - Domain Generation Algorithm Detection

**Description:**  
Analyzes subdomains to identify potential DGA (Domain Generation Algorithm) behavior, which is often associated with malware.

**Syntax:**  
```
/dga <domain>
```

**Parameters:**
- `domain`: The domain to analyze for DGA behavior

**Example:**
```
/dga example.com
```

**Expected Output:**
```
Found 23 suspected DGA domains for 'example.com'.
```

Clicking the "View Results" button will open a modal with detailed information:

```
Domain: qw7xrt92p.example.com
Suspicious Label: qw7xrt92p
DGA Type: Suspected DGA
Probability: 0.9945

Domain: z8mklp56q.example.com
Suspicious Label: z8mklp56q
DGA Type: Suspected DGA
Probability: 0.9912

...
```

**Use Case:**  
This command helps identify potentially malicious subdomains created by malware using domain generation algorithms, which often create randomized domain names to evade detection.

---

### 8. `/dnscount` - DNS Record Count Analysis

**Description:**  
Analyzes DNS record counts for a domain and its subdomains, with optional visualization.

**Syntax:**  
```
/dnscount <domain>
/dnscount -plot <domain>
```

**Parameters:**
- `domain`: The domain to analyze
- `-plot` (Optional): Generate a timeline plot instead of a bar chart

**Example:**
```
/dnscount example.com
/dnscount -plot example.com
```

**Expected Output:**  
The command outputs a visual representation of DNS record counts:

- Without `-plot`: A bar chart showing the top 10 DNS records by count
- With `-plot`: A timeline visualization showing how DNS records have changed over time

The visualization is uploaded as an image to the Slack channel.

**Use Case:**  
This command helps identify unusual patterns in DNS record usage and changes over time, which could indicate potential security issues or infrastructure changes.

---

### 9. `/timeline` - DNS Record Timeline

**Description:**  
Generates a timeline visualization of A/AAAA DNS record changes for a domain.

**Syntax:**  
```
/timeline <domain>
```

**Parameters:**
- `domain`: The domain to generate the timeline for

**Example:**
```
/timeline example.com
```

**Expected Output:**  
The command generates and uploads a visual timeline of DNS record changes, showing when A and AAAA records were added, changed, or removed over time.

**Use Case:**  
This visualization helps identify patterns or anomalies in how DNS records have changed over time, which can be useful for security investigations or infrastructure auditing.

---

### 10. `/screenshot` - Website Screenshot

**Description:**  
Takes a screenshot of a specified URL using browser automation with anti-detection measures.

**Syntax:**  
```
/screenshot <url> [browser_type]
```

**Parameters:**
- `url`: The URL to capture a screenshot of
- `browser_type` (Optional): Browser to use (chromium, firefox, or webkit). Default: chromium

**Example:**
```
/screenshot https://example.com firefox
```

**Expected Output:**  
The command uploads a screenshot of the website to the Slack channel, showing how the page appears in the specified browser.

**Use Case:**  
This command is useful for quickly examining suspicious or phishing websites, capturing visual evidence, or testing web application security without needing to directly visit the site.

## Tips and Best Practices

### Combining Commands for Investigations

1. **Domain Discovery and Assessment**
   - Start with `/subdomains` to identify all subdomains
   - Use `/supplychain` to check for third-party relationships
   - Run `/mx_security` to assess email security
   - Use `/dga` to identify potential malicious subdomains

2. **Threat Hunting**
   - Use `/dns_history` to find relationships between suspicious domains
   - Run `/fingerprint` to generate comprehensive reports
   - Use `/track` to monitor changes over time
   - Check `/timeline` and `/dnscount -plot` to visualize changes

3. **Phishing Investigation**
   - Use `/screenshot` to safely capture suspicious websites
   - Run `/dns_history` to find related domains
   - Check `/mx_security` to verify email authentication

### Result Interpretation

- **DNS History Analysis**: Focus on overlaps that connect multiple entities, especially those with recent timestamps
- **Timeline Visualizations**: Look for sudden changes or additions that correspond to security incidents
- **Supply Chain Analysis**: Pay attention to unexpected third-party integrations or services

## Troubleshooting

### Common Issues and Solutions

1. **No Results Found**
   - Verify that the domain is correctly formatted
   - Try expanding your search to include more domains or related IPs
   - Check that the domain has public DNS records

2. **Command Times Out**
   - For commands that process large datasets (like `/subdomains` for large domains), try narrowing your search
   - Break up analysis into smaller chunks with more specific targets

3. **Image Uploads Fail**
   - If visualization commands fail to upload images, check your Slack permissions
   - Note that visualizations are temporarily stored before being uploaded to Slack

4. **Bot Not in Channel**
   - If you receive a message that the bot couldn't post, make sure it's been invited to the channel
   - You'll need to add the bot to private channels manually

## Conclusion

This Cybersecurity Slack Bot provides powerful tools for security analysis directly within your Slack workspace. By combining these commands, you can conduct comprehensive security investigations without switching between multiple tools and platforms.

For any issues or feature requests, please contact your system administrator.
