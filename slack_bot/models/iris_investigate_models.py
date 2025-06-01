# models/iris_investigate_models.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Contact:
    name: Optional[str]
    org: Optional[str]
    street: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal: Optional[str]
    country: Optional[str]
    phone: Optional[str]
    fax: Optional[str]
    email: List[str] = field(default_factory=list)

@dataclass
class IPInfo:
    address: str
    asn: List[int]
    country_code: str
    isp: str

@dataclass
class DomainRiskComponent:
    name: str
    risk_score: int
    threats: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

@dataclass
class DomainRisk:
    risk_score: int
    components: List[DomainRiskComponent] = field(default_factory=list)

@dataclass
class IrisInvestigateResult:
    domain: str
    create_date: Optional[str]
    expiration_date: Optional[str]
    registrant_name: Optional[str]
    registrant_org: Optional[str]
    registrar: Optional[str]
    registrar_status: List[str] = field(default_factory=list)
    ip: List[IPInfo] = field(default_factory=list)
    name_server: List[str] = field(default_factory=list)
    domain_risk: Optional[DomainRisk] = None
    # Include other fields as needed

@dataclass
class IrisInvestigateResponse:
    results: List[IrisInvestigateResult] = field(default_factory=list)
    # Include other fields as needed

