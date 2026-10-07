import csv
import os
from rapidfuzz import fuzz

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ADDRESS_THRESHOLD = 75


def _load_employees():
    path = os.path.join(DATA_DIR, "employees.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _normalize_phone(p):
    return "".join(ch for ch in (p or "") if ch.isdigit())[-10:]


def check_ghost_vendor(submission: dict):
    employees = _load_employees()
    bank_account = (submission.get("bank_account") or "").strip()
    phone = _normalize_phone(submission.get("contact_phone"))
    address = (submission.get("registered_address") or "").strip()

    for emp in employees:
        reasons = []
        if bank_account and bank_account == emp["bank_account"].strip():
            reasons.append(f"bank account matches employee {emp['name']} ({emp['employee_id']})")
        if phone and phone == _normalize_phone(emp["phone"]):
            reasons.append(f"phone number matches employee {emp['name']} ({emp['employee_id']})")
        if address and fuzz.partial_ratio(address.lower(), emp["address"].lower()) >= ADDRESS_THRESHOLD:
            reasons.append(f"registered address closely matches employee {emp['name']}'s address on file")

        if reasons:
            detail = (
                f"Vendor submission matches internal HR records: {'; '.join(reasons)}. "
                f"This pattern is consistent with an employee billing their own employer "
                f"through a shell vendor."
            )
            return "flagged", detail

    return "passed", "No match found against the employee directory."
