"""Shared catalogue of the application's 40 Australian distribution centres."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DistributionCentre:
    id: str
    name: str
    state: str
    timezone: str


_TIMEZONES = {
    "NSW": "Australia/Sydney",
    "VIC": "Australia/Melbourne",
    "QLD": "Australia/Brisbane",
    "WA": "Australia/Perth",
    "SA": "Australia/Adelaide",
    "ACT": "Australia/Sydney",
    "TAS": "Australia/Hobart",
    "NT": "Australia/Darwin",
}

DISTRIBUTION_CENTRES = tuple(
    DistributionCentre(code, name, state, _TIMEZONES[state])
    for code, name, state in (
        ("DC-SYD-001", "Sydney Metro Hub", "NSW"),
        ("DC-SYD-002", "Sydney West Distribution", "NSW"),
        ("DC-SYD-003", "Sydney North Depot", "NSW"),
        ("DC-MEL-001", "Melbourne Central Hub", "VIC"),
        ("DC-MEL-002", "Melbourne East Depot", "VIC"),
        ("DC-MEL-003", "Melbourne West Warehouse", "VIC"),
        ("DC-BNE-001", "Brisbane Metro Hub", "QLD"),
        ("DC-BNE-002", "Brisbane South Distribution", "QLD"),
        ("DC-BNE-003", "Brisbane North Depot", "QLD"),
        ("DC-PER-001", "Perth Central Hub", "WA"),
        ("DC-PER-002", "Perth North Depot", "WA"),
        ("DC-ADL-001", "Adelaide Metro Hub", "SA"),
        ("DC-ADL-002", "Adelaide South Distribution", "SA"),
        ("DC-CAN-001", "Canberra Central Hub", "ACT"),
        ("DC-HOB-001", "Hobart Distribution Center", "TAS"),
        ("DC-DAR-001", "Darwin Central Hub", "NT"),
        ("DC-NEW-001", "Newcastle Regional Hub", "NSW"),
        ("DC-WOL-001", "Wollongong Depot", "NSW"),
        ("DC-GEE-001", "Geelong Distribution", "VIC"),
        ("DC-BAL-001", "Ballarat Depot", "VIC"),
        ("DC-GLD-001", "Gold Coast Hub", "QLD"),
        ("DC-TWD-001", "Townsville Regional", "QLD"),
        ("DC-CAI-001", "Cairns Distribution", "QLD"),
        ("DC-TOW-001", "Toowoomba Depot", "QLD"),
        ("DC-LAU-001", "Launceston Hub", "TAS"),
        ("DC-BEN-001", "Bendigo Regional", "VIC"),
        ("DC-ALB-001", "Albury-Wodonga Hub", "NSW"),
        ("DC-WAG-001", "Wagga Wagga Depot", "NSW"),
        ("DC-TRA-001", "Traralgon Distribution", "VIC"),
        ("DC-SHP-001", "Shepparton Depot", "VIC"),
        ("DC-BUN-001", "Bunbury Regional Hub", "WA"),
        ("DC-GER-001", "Geraldton Distribution", "WA"),
        ("DC-KAL-001", "Kalgoorlie Depot", "WA"),
        ("DC-MOU-001", "Mount Gambier Hub", "SA"),
        ("DC-WHY-001", "Whyalla Distribution", "SA"),
        ("DC-POR-001", "Port Augusta Depot", "SA"),
        ("DC-DUB-001", "Dubbo Regional Hub", "NSW"),
        ("DC-TAM-001", "Tamworth Distribution", "NSW"),
        ("DC-ARM-001", "Armidale Depot", "NSW"),
        ("DC-ROC-001", "Rockhampton Hub", "QLD"),
    )
)
