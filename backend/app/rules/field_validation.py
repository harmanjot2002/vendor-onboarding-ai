import re

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
REQUIRED_FIELDS = [
    "company_name", "claimed_years_in_business", "claimed_industry",
    "gstin", "contact_email", "contact_phone", "bank_account", "registered_address",
]


def check_required_fields(submission: dict):
    missing = [f for f in REQUIRED_FIELDS if not submission.get(f)]
    if missing:
        return "failed", f"Missing required fields: {', '.join(missing)}"
    return "passed", "All required fields present."


def check_gstin_format(submission: dict):
    gstin = (submission.get("gstin") or "").strip().upper()
    if not GSTIN_RE.match(gstin):
        return "failed", f"GSTIN '{gstin}' does not match the expected 15-character format."
    return "passed", f"GSTIN '{gstin}' is well-formed."


def check_pan_format(submission: dict):
    pan = submission.get("pan")
    if not pan:
        return "passed", "No PAN supplied (optional)."
    pan = pan.strip().upper()
    if not PAN_RE.match(pan):
        return "failed", f"PAN '{pan}' does not match the expected format."
    return "passed", f"PAN '{pan}' is well-formed."
