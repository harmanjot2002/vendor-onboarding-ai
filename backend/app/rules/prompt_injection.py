import re

# Phrases that indicate the document is trying to address instructions to an AI reader,
# rather than simply stating facts about the vendor. Independent of (and a cross-check on)
# the LLM's own self-reported "flagged_instructions" field.
INJECTION_PATTERNS = [
    r"system\s*note",
    r"pre[- ]?verified",
    r"mark\s+(all\s+)?checks?\s+as\s+passed",
    r"ignore\s+(the\s+)?(previous|above)\s+instructions?",
    r"this\s+vendor\s+has\s+been\s+(approved|verified)\s+by",
    r"approved\s+by\s+the?\s*finance\s+team",
    r"do\s+not\s+flag",
    r"automatically\s+approve",
    r"assistant\s*:",
    r"you\s+are\s+an?\s+ai",
]
COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def scan_for_injection(raw_text: str):
    if not raw_text:
        return "passed", "No document text to scan."
    matched_phrases = []
    for pattern in COMPILED:
        for m in pattern.finditer(raw_text):
            matched_phrases.append(m.group().strip())
    if matched_phrases:
        unique = list(dict.fromkeys(matched_phrases))[:6]
        quoted = ", ".join(f"“{p}”" for p in unique)
        detail = f"Document contains instruction-like text addressed to an AI reader: {quoted}."
        return "flagged", detail
    return "passed", "No instruction-like text found in the extracted document content."
