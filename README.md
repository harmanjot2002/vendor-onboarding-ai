# Vendor Onboarding Automation

**A vendor submits their details and a certificate. The system decides — Approved, Pending, or Rejected — and shows exactly why at every step.**

Built for Zamp's AI Solutions Associate case study (PS-2: Vendor Onboarding). One core design principle drives the whole system:

> **The AI reads. The rules decide.**
> An LLM extracts and summarizes unstructured document content. It never makes the approve/reject call — that always comes from deterministic rule code. This is what turns a prompt-injection attack from a vulnerability into a non-event (see it in action below).

---

## See it in action

<img src="docs/screenshots/submit.png" alt="Submit tab — core scenarios and additional edge cases" width="100%" />

Four flagship scenarios up front, six more edge cases available underneath — same pipeline behind all of them.

<img src="docs/screenshots/live_run_done.png" alt="Live run view — stage-by-stage timeline ending in a decision" width="100%" />

Every stage of the pipeline is visible as it executes, with the reasoning for each check spelled out in plain language.

<img src="docs/screenshots/dashboard.png" alt="Dashboard — run history with status and routing" width="100%" />

---

## How it works

```mermaid
flowchart TD
    A["Vendor submission + certificate PDF"] --> B{"Document complete?"}
    B -- "no" --> B1["Draft follow-up email\nstatus: Pending Documents"]
    B1 -. "vendor resubmits — same run continues" .-> B
    B -- "yes" --> C["Intake & schema validation"]
    C --> D["Document ingestion\n(text + PDF metadata)"]
    D --> E["Prompt-injection scan\n(raw text, no AI)"]
    D --> F["PDF metadata forensics"]
    D --> G["LLM-assisted extraction\nreads only — never decides"]
    C --> H["CIN decode"]
    C --> I["GSTIN internal checks\n(checksum, embedded PAN, state code)"]
    C --> J["Bank account holder name check"]
    C --> K["Bank-change / BEC check"]
    C --> L["Ghost vendor check\n(employee cross-reference)"]
    C --> M["Homoglyph check\n(look-alike vendor name)"]
    E & F & G & H & I & J & K & L & M --> N{"Risk scoring & decision"}
    N -- "clean" --> O["Approved"]
    N -- "needs a human" --> P["Pending\n+ routed to Procurement / Internal Audit / Finance Verification"]
    N -- "bad-faith signal" --> Q["Rejected"]
```

Every stage writes its result to the database as it completes — that's what the live run view polls and renders, and what the dashboard's history is built from.

Full architecture notes and a sample case for every scenario: **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)**

---

## The scenarios

### Core (led with in the demo)

| Scenario | Category | Outcome |
|---|---|---|
| Happy path — clean vendor | Baseline | **Approved** |
| Prompt injection in certificate | AI security | **Rejected** |
| Bank-detail change (BEC pattern) | Insider fraud | **Pending** → Finance Verification |
| Incomplete submission → resubmit → approved | Workflow | **Pending Documents** → Approved |

<details>
<summary><strong>Additional edge cases</strong> — same pipeline, narrower judgment calls</summary>

| Scenario | Category | Outcome |
|---|---|---|
| Perfect forgery (PDF metadata mismatch) | Document forensics | **Pending** |
| Ghost vendor (employee self-billing) | Insider fraud | **Pending** → Internal Audit |
| Homoglyph impersonation | Impersonation | **Rejected** |
| CIN decode mismatch | Identity check | **Pending** |
| Proprietorship bank-name mismatch | Identity check | **Pending** |
| GSTIN / address state mismatch | Identity check | **Pending** |
| GSTIN checksum failure (likely typo) | Identity check | **Pending** |

</details>

---

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy + SQLite, Uvicorn
- **Documents:** `pypdf` (text + metadata extraction), `reportlab` (test certificate generation)
- **Fraud/identity logic:** `rapidfuzz` (fuzzy name/address matching), a hand-rolled GSTIN mod-36 checksum, a CIN structural parser, a Unicode homoglyph skeleton matcher
- **LLM:** Anthropic or OpenAI, auto-detected from whichever API key is set — used only for document reading/summarizing, never for the decision
- **Frontend:** plain HTML/CSS/JS, no framework, no build step — served directly by FastAPI as static files

One Python process, one deploy command.

<details>
<summary><strong>Project structure</strong></summary>

```
vendor-onboarding-ai/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI routes
│       ├── orchestrator.py      # runs the pipeline stage-by-stage
│       ├── database.py          # SQLAlchemy models (Run, RunStage)
│       ├── models.py            # Pydantic schemas
│       ├── rules/               # one module per check
│       ├── services/            # PDF extraction + LLM extraction
│       └── data/
│           ├── employees.csv          # ghost-vendor cross-reference
│           ├── existing_vendors.csv   # homoglyph + BEC cross-reference
│           ├── nic_codes.json         # CIN industry-code lookup
│           └── scenarios/             # the 11 bundled demo scenarios
├── frontend/                    # vanilla HTML/CSS/JS, served as static files
├── test_data/
│   └── generate_test_pdfs.py    # regenerates every scenario's PDF + JSON
├── docs/
│   ├── DOCUMENTATION.md         # architecture + a worked sample per scenario
│   └── screenshots/
└── render.yaml
```

</details>

---

## Running it locally

```bash
git clone https://github.com/harmanjot2002/vendor-onboarding-ai.git
cd vendor-onboarding-ai
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
echo "ANTHROPIC_API_KEY=sk-ant-..." > backend/.env   # or OPENAI_API_KEY=sk-...
cd backend && uvicorn app.main:app --reload --port 8010
```

Open `http://localhost:8010`.

| Variable | Required? | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | Tried first if both keys are set |
| `OPENAI_API_KEY` | No | Falls back to `gpt-4o-mini` if this is the only one set |

Neither key is required to run the app — the LLM-extraction stage just reports itself as skipped, and every rule-based check still runs normally.

---

## Deployment

Configured for [Render](https://render.com) via [`render.yaml`](render.yaml) — connect this repo as a Web Service and it auto-detects the build/start commands. See **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md#deploying-to-render)** for the full walkthrough.

---

## Known limitations

- No OCR — every bundled test document has a real text layer; a scanned image-only certificate would fail at document ingestion.
- Fuzzy-match thresholds are hand-tuned against this test dataset, not fit against a labeled historical corpus.
- SQLite is right-sized for a demo; Render's free-tier disk isn't guaranteed to persist across deploys. A production deployment would move to Postgres — a one-line change to `database.py`.
- No auth layer on the admin UI.
