import re
import datetime as dt

# Producer/Creator strings we'd expect from a government e-portal export.
EXPECTED_PORTAL_TOOLS = ["itext", "gst portal", "nic", "e-portal", "government"]
SUSPICIOUS_TOOLS = ["canva", "photoshop", "illustrator", "figma", "sketch", "word"]


def _parse_pdf_date(value):
    if not value:
        return None
    # pypdf gives dates like "D:20250131120000+05'30'" or a datetime already
    if isinstance(value, dt.datetime):
        return value
    s = str(value)
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", s)
    if m:
        year, month, day = map(int, m.groups())
        try:
            return dt.datetime(year, month, day)
        except ValueError:
            return None
    return None


def check_pdf_metadata(metadata: dict, claimed_issue_year: int | None):
    creator = (metadata.get("/Creator") or metadata.get("Creator") or "").lower()
    producer = (metadata.get("/Producer") or metadata.get("Producer") or "").lower()
    combined = f"{creator} {producer}"

    flags = []
    for tool in SUSPICIOUS_TOOLS:
        if tool in combined:
            flags.append(f"Creator/Producer metadata mentions '{tool}', not a government e-portal export")

    created = _parse_pdf_date(metadata.get("/CreationDate") or metadata.get("CreationDate"))
    modified = _parse_pdf_date(metadata.get("/ModDate") or metadata.get("ModDate"))

    if created and claimed_issue_year and created.year != claimed_issue_year:
        flags.append(
            f"PDF creation timestamp is {created.date()}, but the certificate claims to have "
            f"been issued in {claimed_issue_year}"
        )
    if created and (dt.datetime.utcnow() - created).days < 7:
        flags.append(f"PDF was created only {(dt.datetime.utcnow() - created).days} day(s) ago")

    if flags:
        return "flagged", "; ".join(flags)
    return "passed", "PDF metadata is consistent with a portal-issued document."
