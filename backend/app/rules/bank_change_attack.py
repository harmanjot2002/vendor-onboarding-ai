import csv
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_existing_vendors():
    path = os.path.join(DATA_DIR, "existing_vendors.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_bank_change_attack(submission: dict):
    vendors = _load_existing_vendors()
    name = (submission.get("company_name") or "").strip()
    domain = (submission.get("contact_email") or "").split("@")[-1].strip()
    bank_account = (submission.get("bank_account") or "").strip()

    for v in vendors:
        if v["name"].strip() != name or not v.get("bank_account_on_file"):
            continue

        on_file_bank = v["bank_account_on_file"].strip()
        on_file_domain = (v.get("domain") or "").strip()
        bank_changed = bool(bank_account) and bank_account != on_file_bank
        domain_changed = bool(domain) and bool(on_file_domain) and domain != on_file_domain

        if bank_changed and domain_changed:
            known_phone = v.get("known_phone", "N/A")
            detail = (
                f"'{name}' is an existing approved vendor. This submission changes the bank account "
                f"on file ({on_file_bank} → {bank_account}) AND arrives from a new email domain "
                f"({on_file_domain} → {domain}) — the classic business-email-compromise pattern. "
                f"Holding for out-of-band verification: call the vendor's known contact number on "
                f"file ({known_phone}) to confirm the change by voice. Do not use any contact details "
                f"supplied in this submission."
            )
            return "flagged", detail

        if bank_changed:
            return (
                "passed",
                f"Bank account differs from the one on file, but the request still comes from the "
                f"vendor's known email domain ({on_file_domain}) — lower risk. Still recommend "
                f"standard confirmation before paying out.",
            )

    return "passed", "No existing-vendor bank-change pattern detected."
