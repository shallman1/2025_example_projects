# models/dnsdb_models.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DnsdbRecord:
    rrname: str
    rrtype: str
    rdata: List[str]
    time_first: Optional[int]
    time_last: Optional[int]
    count: Optional[int]
    bailiwick: Optional[str]
