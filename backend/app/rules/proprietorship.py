from rapidfuzz import fuzz

NAME_MATCH_THRESHOLD = 65
PAN_ENTITY_TYPE_INDIVIDUAL = "P"


def check_bank_holder_name(submission: dict):
    holder = (submission.get("bank_account_holder_name") or "").strip()
    company = (submission.get("company_name") or "").strip()
    pan = (submission.get("pan") or "").strip().upper()

    if not holder:
        return "passed", "No bank account holder name supplied — skipping this check."

    similarity = fuzz.token_sort_ratio(holder.lower(), company.lower())
    if similarity >= NAME_MATCH_THRESHOLD:
        return "passed", f"Bank account holder name '{holder}' is consistent with company name '{company}'."

    entity_type = pan[3] if len(pan) == 10 else None
    if entity_type == PAN_ENTITY_TYPE_INDIVIDUAL:
        return (
            "flagged_soft",
            f"Bank account is held in the name '{holder}', not the company name '{company}' — but "
            f"the PAN's 4th character ('P') identifies this as a sole proprietorship, where billing "
            f"in the proprietor's personal name is normal and expected. Requesting a proprietorship "
            f"declaration rather than rejecting.",
        )

    return (
        "flagged_hard",
        f"Bank account is held in the name '{holder}', not the company name '{company}', and the "
        f"PAN does not indicate a sole proprietorship (entity type code: '{entity_type or 'unknown'}'). "
        f"This needs manual verification before the bank detail can be trusted.",
    )
