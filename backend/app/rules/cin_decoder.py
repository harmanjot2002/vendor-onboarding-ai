import re
import json
import os
import datetime as dt
from rapidfuzz import fuzz

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CIN_RE = re.compile(r"^([LU])(\d{5})([A-Z]{2})(\d{4})([A-Z]{3})(\d{6})$")

STATE_NAMES = {
    "MH": "Maharashtra", "KA": "Karnataka", "TN": "Tamil Nadu", "DL": "Delhi",
    "WB": "West Bengal", "TG": "Telangana", "GJ": "Gujarat", "HR": "Haryana",
    "UP": "Uttar Pradesh", "RJ": "Rajasthan", "PB": "Punjab",
}

INDUSTRY_KEYWORD_RELEVANCE_THRESHOLD = 45


def _load_nic_codes():
    with open(os.path.join(DATA_DIR, "nic_codes.json"), encoding="utf-8") as f:
        return json.load(f)


def decode_cin(cin: str):
    m = CIN_RE.match(cin.strip().upper())
    if not m:
        return None
    listing, nic, state, year, ctype, reg = m.groups()
    return {
        "listing_status": "Listed" if listing == "L" else "Unlisted",
        "nic_code": nic,
        "state_code": state,
        "state_name": STATE_NAMES.get(state, state),
        "incorporation_year": int(year),
        "company_type": ctype,
        "registration_number": reg,
    }


def check_cin(submission: dict):
    cin = submission.get("cin")
    if not cin:
        return "passed", "No CIN supplied (optional field)."

    decoded = decode_cin(cin)
    if not decoded:
        return "flagged", f"CIN '{cin}' does not match the expected 21-character CIN structure."

    nic_codes = _load_nic_codes()
    industry_desc = nic_codes.get(decoded["nic_code"], "Unknown industry (NIC code not in lookup table)")
    claimed_industry = (submission.get("claimed_industry") or "")
    claimed_years = submission.get("claimed_years_in_business") or 0

    mismatches = []

    relevance = fuzz.partial_ratio(claimed_industry.lower(), industry_desc.lower())
    if relevance < INDUSTRY_KEYWORD_RELEVANCE_THRESHOLD:
        mismatches.append(
            f"CIN industry code {decoded['nic_code']} decodes to '{industry_desc}', which does not "
            f"match the claimed industry '{claimed_industry}'"
        )

    current_year = dt.datetime.utcnow().year
    implied_min_incorporation_year = current_year - int(claimed_years)
    if decoded["incorporation_year"] > implied_min_incorporation_year:
        mismatches.append(
            f"CIN shows incorporation in {decoded['incorporation_year']}, but the vendor claims "
            f"{claimed_years} years in business (would require incorporation by "
            f"{implied_min_incorporation_year} or earlier)"
        )

    address = (submission.get("registered_address") or "")
    if decoded["state_name"].lower() not in address.lower() and decoded["state_code"].lower() not in address.lower():
        mismatches.append(
            f"CIN state code {decoded['state_code']} ({decoded['state_name']}) does not appear in the "
            f"registered address '{address}'"
        )

    detail_prefix = (
        f"CIN decoded: {decoded['listing_status']}, NIC {decoded['nic_code']} ({industry_desc}), "
        f"state {decoded['state_code']}, incorporated {decoded['incorporation_year']}, "
        f"type {decoded['company_type']}. "
    )

    if mismatches:
        return "flagged", detail_prefix + " | ".join(mismatches)
    return "passed", detail_prefix + "Consistent with the vendor's claims."
