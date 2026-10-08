from pydantic import BaseModel
from typing import Optional


class Submission(BaseModel):
    company_name: str
    claimed_years_in_business: int
    claimed_industry: str
    claimed_issue_year: Optional[int] = None
    gstin: str
    cin: Optional[str] = None
    udyam_number: Optional[str] = None
    pan: Optional[str] = None
    contact_email: str
    contact_phone: str
    bank_account: str
    bank_account_holder_name: Optional[str] = None
    registered_address: str


class StageOut(BaseModel):
    order_index: int
    stage_name: str
    status: str
    detail: str

    class Config:
        from_attributes = True


class RunOut(BaseModel):
    id: int
    scenario_key: Optional[str]
    vendor_name: str
    status: str
    routing: str
    reason_summary: str
    stages: list[StageOut]

    class Config:
        from_attributes = True


class RunSummaryOut(BaseModel):
    id: int
    scenario_key: Optional[str]
    vendor_name: str
    status: str
    routing: str
    reason_summary: str

    class Config:
        from_attributes = True
