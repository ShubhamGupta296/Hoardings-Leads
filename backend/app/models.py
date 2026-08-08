from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Hoarding(BaseModel):
    site_id: str
    location: str
    size_sqft: int
    traffic_score: float
    monthly_rate_inr: int
    rate_band: str = Field(description="Rate band: low (<200k), mid (200k-300k), high (>300k)")


class Customer(BaseModel):
    customer_id: str
    name: str
    industry: str
    budget_band: str = Field(description="Budget band: low, mid, high")
    relationship_score: int = Field(description="Scale 1 to 10")
    last_contact_date: str


class Booking(BaseModel):
    booking_id: str
    site_id: str
    customer_id: str
    start_date: str
    end_date: str
    value_inr: int


class VacancyResponse(BaseModel):
    site_id: str
    location: str
    size_sqft: int
    traffic_score: float
    monthly_rate_inr: int
    rate_band: str
    end_date: str
    free_from: str
    days_until_vacant: int
    current_occupant_id: Optional[str] = None
    current_occupant_name: Optional[str] = None


class LeadScoreBreakdown(BaseModel):
    site_history: float
    total_history: float
    budget_fit: float
    industry_fit: float
    relationship: float
    contact_recency: float


class LeadResponse(BaseModel):
    customer_id: str
    customer_name: str
    industry: str
    budget_band: str
    relationship_score: int
    last_contact_date: str
    total_score: float
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None
    breakdown: LeadScoreBreakdown
    reasons: List[str]
    incumbent_status: bool = False


class LeadsForSiteResponse(BaseModel):
    site_id: str
    location: str
    monthly_rate_inr: int
    rate_band: str
    leads_count: int
    leads: List[LeadResponse]


class PitchRequest(BaseModel):
    site_id: str
    customer_id: str


class PitchResponse(BaseModel):
    site_id: str
    customer_id: str
    site_location: str
    customer_name: str
    quoted_rate_inr: int
    pitch_text: str
    generated_by_ai: bool
    grounding_facts: Dict[str, Any]
