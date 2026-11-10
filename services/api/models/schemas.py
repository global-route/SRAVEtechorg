from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Building(BaseModel):
    id: int
    lga_id: str
    footprint: str           # GeoJSON polygon string
    confidence_score: float
    property_type: str       # residential_low | residential_high | commercial | industrial
    verified: bool
    scan_date: datetime
    created_at: datetime


class TaxAssessment(BaseModel):
    id: int
    building_id: int
    owner_phone: Optional[str]
    amount_due: float
    wa_status: str           # pending | delivered | read | paid
    payment_ref: Optional[str]
    assessed_at: datetime


class GapAnalysis(BaseModel):
    lga_id: str
    total_detected_buildings: int
    registered_tax_payers: int
    unregistered_gap: int
    estimated_annual_revenue_gap_ngn: float
    compliance_percentage: float


class VerifyPayload(BaseModel):
    verified: bool
    owner_phone: str
    photo_url: Optional[str] = None
    notes: Optional[str] = None
    property_type: Optional[str] = None
    owner_language: Optional[str] = None
