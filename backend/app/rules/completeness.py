def check_completeness(has_document: bool, company_name: str):
    if has_document:
        return "passed", "All required documents are attached."

    missing = ["GST registration certificate (PDF)"]
    email_draft = (
        f"Subject: Action required — missing document for {company_name}'s onboarding\n\n"
        f"Hi,\n\n"
        f"Thanks for submitting your vendor onboarding form. Before we can review it, we need "
        f"the following:\n"
        + "\n".join(f"  - {item}" for item in missing)
        + "\n\n"
        f"Please reply with the missing document and we'll continue processing immediately — "
        f"no need to resubmit anything else.\n\n"
        f"Best,\nProcurement Team"
    )
    detail = (
        f"Missing: {', '.join(missing)}. Drafted the following email to the vendor:\n\n{email_draft}"
    )
    return "incomplete", detail
