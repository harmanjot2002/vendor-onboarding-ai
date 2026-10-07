import csv
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Common lookalike characters (Cyrillic/Greek -> Latin) used in impersonation attacks.
LOOKALIKE_MAP = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ј": "j", "ѕ": "s", "А": "A", "Е": "E", "О": "O", "Р": "P",
    "С": "C", "У": "Y", "Х": "X", "Ι": "I", "Κ": "K", "Μ": "M", "Ο": "O",
    "Τ": "T", "ο": "o", "α": "a", "ν": "v", "ρ": "p",
}


def _load_existing_vendors():
    path = os.path.join(DATA_DIR, "existing_vendors.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def skeletonize(s: str) -> str:
    return "".join(LOOKALIKE_MAP.get(ch, ch) for ch in s).lower()


def find_lookalike_chars(s: str):
    return [(i, ch) for i, ch in enumerate(s) if ch in LOOKALIKE_MAP]


def check_homoglyph(submission: dict):
    vendors = _load_existing_vendors()
    name = (submission.get("company_name") or "").strip()
    domain = (submission.get("contact_email") or "").split("@")[-1].strip()

    name_skeleton = skeletonize(name)
    domain_skeleton = skeletonize(domain)

    for v in vendors:
        existing_name_skeleton = skeletonize(v["name"])
        existing_domain_skeleton = skeletonize(v["domain"])

        name_collision = name_skeleton == existing_name_skeleton and name != v["name"]
        domain_collision = domain and domain_skeleton == existing_domain_skeleton and domain != v["domain"]

        if name_collision or domain_collision:
            suspects = find_lookalike_chars(name) + find_lookalike_chars(domain)
            char_list = ", ".join(f"position {i} ('{ch}' U+{ord(ch):04X})" for i, ch in suspects) or "none found"
            detail = (
                f"'{name}' / '{domain}' is visually identical to the existing approved vendor "
                f"'{v['name']}' / '{v['domain']}' but is a different string — likely a look-alike "
                f"(homoglyph) character substitution. Suspect characters: {char_list}."
            )
            return "flagged", detail

    return "passed", "No look-alike collision found against the existing vendor list."
