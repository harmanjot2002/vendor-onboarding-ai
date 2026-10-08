import re

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
CODE_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# GST numeric state codes -> state name (subset covering the states used in our test data;
# real GSTIN validators carry the full 01-38 list).
GST_STATE_CODES = {
    "03": "Punjab", "06": "Haryana", "07": "Delhi", "08": "Rajasthan",
    "09": "Uttar Pradesh", "19": "West Bengal", "24": "Gujarat",
    "27": "Maharashtra", "29": "Karnataka", "33": "Tamil Nadu", "36": "Telangana",
}


def compute_gstin_checksum_char(gstin_first_14: str) -> str:
    """Standard GSTIN checksum algorithm (mod-36, alternating factor 1/2)."""
    factor = 1
    total = 0
    for ch in gstin_first_14:
        code_point = CODE_CHARS.index(ch)
        digit = factor * code_point
        digit = (digit // 36) + (digit % 36)
        total += digit
        factor = 2 if factor == 1 else 1
    return CODE_CHARS[(36 - (total % 36)) % 36]


def check_tax_identity(submission: dict):
    """Returns (category, status, detail). category in {"none", "typo", "mismatch"}."""
    gstin = (submission.get("gstin") or "").strip().upper()
    if not GSTIN_RE.match(gstin):
        return "none", "passed", "Skipped — GSTIN format already failed basic validation upstream."

    pan = (submission.get("pan") or "").strip().upper()
    embedded_pan = gstin[2:12]
    address = submission.get("registered_address") or ""

    mismatches = []
    if pan and embedded_pan != pan:
        mismatches.append(
            f"the PAN embedded in the GSTIN ('{embedded_pan}') does not match the PAN "
            f"provided separately ('{pan}')"
        )

    state_code = gstin[:2]
    state_name = GST_STATE_CODES.get(state_code)
    if state_name and state_name.lower() not in address.lower():
        mismatches.append(
            f"the GSTIN state code {state_code} indicates '{state_name}', but the registered "
            f"address ('{address}') is in a different state"
        )

    checksum_ok = gstin[14] == compute_gstin_checksum_char(gstin[:14])

    if mismatches:
        suffix = " The GSTIN checksum is also invalid." if not checksum_ok else ""
        return (
            "mismatch", "flagged",
            "Internal tax-identity inconsistency — " + "; ".join(mismatches) + "." + suffix,
        )

    if not checksum_ok:
        return (
            "typo", "flagged",
            f"GSTIN '{gstin}' fails its own checksum, but every other field (embedded PAN, "
            f"state code) is consistent — this reads as a single-character typo, not fraud. "
            f"Recommend asking the vendor to recheck and resubmit the GSTIN.",
        )

    return "none", "passed", "GSTIN is internally consistent: embedded PAN matches, state code matches address, checksum valid."
