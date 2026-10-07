import time

from .database import Run, RunStage
from .services.pdf_extract import extract_text_and_metadata
from .services.llm_extract import extract_fields_from_document
from .rules import field_validation, prompt_injection, pdf_forensics, ghost_vendor, homoglyph, cin_decoder

STAGE_DELAY_SECONDS = 0.5  # purely cosmetic — lets the live run view visibly step through stages


def _add_stage(db, run: Run, order_index: int, name: str, status: str, detail: str):
    stage = RunStage(run_id=run.id, order_index=order_index, stage_name=name, status=status, detail=detail)
    db.add(stage)
    db.commit()
    time.sleep(STAGE_DELAY_SECONDS)
    return stage


def run_pipeline(db, run_id: int, submission: dict, pdf_bytes: bytes | None):
    run = db.get(Run, run_id)
    idx = 0
    flags = {}  # stage_key -> detail string, only set when status != "passed"

    # Stage 1: Intake & schema validation
    idx += 1
    status, detail = field_validation.check_required_fields(submission)
    if status == "passed":
        gstin_status, gstin_detail = field_validation.check_gstin_format(submission)
        pan_status, pan_detail = field_validation.check_pan_format(submission)
        if gstin_status == "failed":
            status, detail = gstin_status, gstin_detail
        elif pan_status == "failed":
            status, detail = pan_status, pan_detail
        else:
            detail = f"{detail} {gstin_detail} {pan_detail}"
    _add_stage(db, run, idx, "Intake & schema validation", status, detail)
    if status == "failed":
        flags["hard_fail"] = detail

    # Stage 2: Document ingestion
    idx += 1
    doc_text, doc_metadata = "", {}
    if pdf_bytes:
        try:
            extracted = extract_text_and_metadata(pdf_bytes)
            doc_text, doc_metadata = extracted["text"], extracted["metadata"]
            _add_stage(db, run, idx, "Document ingestion", "passed",
                       f"Extracted {extracted['num_pages']} page(s) of text and PDF metadata.")
        except Exception as exc:
            _add_stage(db, run, idx, "Document ingestion", "failed", f"Could not read PDF: {exc}")
    else:
        _add_stage(db, run, idx, "Document ingestion", "skipped", "No document uploaded for this submission.")

    # Stage 2a: Prompt-injection scan (independent of the LLM)
    idx += 1
    inj_status, inj_detail = prompt_injection.scan_for_injection(doc_text)
    _add_stage(db, run, idx, "Prompt-injection scan (raw text)", inj_status, inj_detail)
    if inj_status == "flagged":
        flags["prompt_injection"] = inj_detail

    # Stage 2b: PDF forensics
    idx += 1
    if doc_metadata:
        claimed_year = submission.get("claimed_issue_year")
        forensics_status, forensics_detail = pdf_forensics.check_pdf_metadata(doc_metadata, claimed_year)
        _add_stage(db, run, idx, "PDF metadata forensics", forensics_status, forensics_detail)
        if forensics_status == "flagged":
            flags["pdf_forensics"] = forensics_detail
    else:
        _add_stage(db, run, idx, "PDF metadata forensics", "skipped", "No PDF metadata available.")

    # Stage 3: LLM-assisted extraction (reads, never decides)
    idx += 1
    if doc_text:
        llm_result = extract_fields_from_document(doc_text)
        llm_detail = llm_result.get("summary", "")
        if llm_result.get("flagged_instructions"):
            llm_detail += " | LLM independently flagged embedded instructions: " + "; ".join(
                llm_result["flagged_instructions"]
            )
            flags.setdefault("prompt_injection", llm_detail)
            llm_status = "flagged"
        elif llm_result.get("_llm_skipped"):
            llm_status = "skipped"
        else:
            llm_status = "passed"
        _add_stage(db, run, idx, "LLM-assisted extraction (reads, does not decide)", llm_status, llm_detail)
    else:
        _add_stage(db, run, idx, "LLM-assisted extraction (reads, does not decide)", "skipped", "No document text to extract from.")

    # Stage 4: Identity consistency (CIN decode)
    idx += 1
    cin_status, cin_detail = cin_decoder.check_cin(submission)
    _add_stage(db, run, idx, "Identity consistency — CIN decode", cin_status, cin_detail)
    if cin_status == "flagged":
        flags["cin_mismatch"] = cin_detail

    # Stage 5a: Ghost vendor cross-check
    idx += 1
    gv_status, gv_detail = ghost_vendor.check_ghost_vendor(submission)
    _add_stage(db, run, idx, "Fraud check — employee cross-reference", gv_status, gv_detail)
    if gv_status == "flagged":
        flags["ghost_vendor"] = gv_detail

    # Stage 5b: Homoglyph impersonation check
    idx += 1
    hg_status, hg_detail = homoglyph.check_homoglyph(submission)
    _add_stage(db, run, idx, "Fraud check — look-alike vendor name/domain", hg_status, hg_detail)
    if hg_status == "flagged":
        flags["homoglyph"] = hg_detail

    # Stage 6: Risk scoring & decision (deterministic, priority-ordered)
    idx += 1
    status_final, reason, routing = _decide(flags)
    _add_stage(db, run, idx, "Risk scoring & decision", "passed", reason)

    run.status = status_final
    run.routing = routing
    run.reason_summary = reason
    db.add(run)
    db.commit()


def _decide(flags: dict):
    if "hard_fail" in flags:
        return "rejected", f"Rejected — {flags['hard_fail']}", "procurement"
    if "prompt_injection" in flags:
        return (
            "rejected",
            f"Rejected — document contains embedded instructions directed at an automated "
            f"reviewer. Decision made by rules, not affected by the injected text. "
            f"({flags['prompt_injection']})",
            "procurement",
        )
    if "homoglyph" in flags:
        return "rejected", f"Rejected — impersonation of an existing approved vendor. {flags['homoglyph']}", "procurement"
    if "ghost_vendor" in flags:
        return (
            "pending",
            f"Pending — escalated to Internal Audit, not the standard procurement approver. {flags['ghost_vendor']}",
            "internal_audit",
        )
    if "pdf_forensics" in flags:
        return (
            "pending",
            f"Pending — please request a fresh copy of the certificate downloaded directly "
            f"from the issuing portal. {flags['pdf_forensics']}",
            "procurement",
        )
    if "cin_mismatch" in flags:
        return "pending", f"Pending — enhanced due diligence required. {flags['cin_mismatch']}", "procurement"
    return "approved", "Approved — all checks passed.", "procurement"
