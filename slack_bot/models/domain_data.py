# models/domain_data.py

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class DomainData:
    domain: str
    attributes: Dict[str, Any]

    def __post_init__(self):
        # Perform any necessary initialization or validation here
        pass
