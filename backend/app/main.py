import os
import json
import glob

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import init_db, get_session, Run
from .models import RunOut, RunSummaryOut
from .orchestrator import run_pipeline

APP_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.dirname(APP_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")
SCENARIOS_DIR = os.path.join(APP_DIR, "data", "scenarios")

app = FastAPI(title="Vendor Onboarding Automation")


@app.on_event("startup")
def on_startup():
    init_db()


def _run_to_dict(run: Run):
    return RunOut.model_validate(run).model_dump()


@app.get("/api/scenarios")
def list_scenarios():
    scenarios = []
    for path in sorted(glob.glob(os.path.join(SCENARIOS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        scenarios.append(data["meta"])
    return scenarios


@app.post("/api/scenarios/{key}/run")
def run_scenario(key: str, background_tasks: BackgroundTasks):
    json_path = os.path.join(SCENARIOS_DIR, f"{key}.json")
    pdf_path = os.path.join(SCENARIOS_DIR, f"{key}.pdf")
    if not os.path.exists(json_path):
        raise HTTPException(404, f"Unknown scenario '{key}'")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    submission = data["submission"]
    pdf_bytes = None
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    db = get_session()
    try:
        run = Run(
            scenario_key=key,
            vendor_name=submission.get("company_name", "Unknown vendor"),
            status="running",
            submission_json=json.dumps(submission),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    background_tasks.add_task(_execute_pipeline, run_id, submission, pdf_bytes)
    return {"run_id": run_id}


@app.post("/api/submit")
async def submit_vendor(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    claimed_years_in_business: int = Form(...),
    claimed_industry: str = Form(...),
    claimed_issue_year: int | None = Form(None),
    gstin: str = Form(...),
    cin: str | None = Form(None),
    udyam_number: str | None = Form(None),
    pan: str | None = Form(None),
    contact_email: str = Form(...),
    contact_phone: str = Form(...),
    bank_account: str = Form(...),
    registered_address: str = Form(...),
    document: UploadFile | None = File(None),
):
    submission = {
        "company_name": company_name,
        "claimed_years_in_business": claimed_years_in_business,
        "claimed_industry": claimed_industry,
        "claimed_issue_year": claimed_issue_year,
        "gstin": gstin,
        "cin": cin,
        "udyam_number": udyam_number,
        "pan": pan,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "bank_account": bank_account,
        "registered_address": registered_address,
    }
    pdf_bytes = await document.read() if document is not None else None

    db = get_session()
    try:
        run = Run(
            scenario_key=None,
            vendor_name=company_name,
            status="running",
            submission_json=json.dumps(submission),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    background_tasks.add_task(_execute_pipeline, run_id, submission, pdf_bytes)
    return {"run_id": run_id}


def _execute_pipeline(run_id: int, submission: dict, pdf_bytes: bytes | None):
    db = get_session()
    try:
        run_pipeline(db, run_id, submission, pdf_bytes)
    finally:
        db.close()


@app.get("/api/runs")
def list_runs():
    db = get_session()
    try:
        runs = db.query(Run).order_by(Run.id.desc()).all()
        return [RunSummaryOut.model_validate(r).model_dump() for r in runs]
    finally:
        db.close()


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    db = get_session()
    try:
        run = db.get(Run, run_id)
        if run is None:
            raise HTTPException(404, "Run not found")
        return _run_to_dict(run)
    finally:
        db.close()


# Static frontend (mounted last so /api/* routes above take precedence)
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
