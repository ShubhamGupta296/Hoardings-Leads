from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from app.models import (
    VacancyResponse,
    LeadsForSiteResponse,
    PitchRequest,
    PitchResponse
)
from app.data_loader import load_all_datasets
from app.pipeline import get_upcoming_vacancies
from app.scoring import calculate_lead_scores
from app.pitch import generate_pitch

app = FastAPI(
    title="Smart Leads Agent for Hoardings API",
    description="Backend API for detecting upcoming billboard vacancies, scoring best-fit lead customers with explicit reasons, and generating grounded pitch offers.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Root Welcome & API Index")
def root_index():
    return {
        "message": "Welcome to Smart Leads Agent for Hoardings API!",
        "documentation": "/docs",
        "health_check": "/api/health",
        "endpoints": {
            "vacancies": "/api/vacancies",
            "leads_for_site": "/api/leads/{site_id}",
            "generate_pitch": "/api/pitch [POST]"
        }
    }



@app.get("/api/health", summary="System Health & Dataset Status")
def health_check():
    try:
        hoardings_df, customers_df, bookings_df = load_all_datasets()
        return {
            "status": "healthy",
            "datasets": {
                "hoardings_count": len(hoardings_df),
                "customers_count": len(customers_df),
                "bookings_count": len(bookings_df)
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(exc)}")


@app.get("/api/vacancies", response_model=List[VacancyResponse], summary="Detect Upcoming Vacancies (Next 90 Days)")
def get_vacancies(
    max_days: int = Query(90, ge=1, le=365, description="Vacancy lookahead window in days"),
    ref_date: Optional[str] = Query("2026-08-08", description="Reference date (YYYY-MM-DD) for window calculation")
):
    """
    Returns all hoarding sites with bookings ending in the next `max_days` (default 90)
    that have no follow-on booking scheduled.
    """
    try:
        hoardings_df, customers_df, bookings_df = load_all_datasets()
        vacancies = get_upcoming_vacancies(
            hoardings_df=hoardings_df,
            bookings_df=bookings_df,
            customers_df=customers_df,
            reference_date_str=ref_date,
            max_days=max_days
        )
        return vacancies
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error calculating vacancies: {str(exc)}")


@app.get("/api/leads/{site_id}", response_model=LeadsForSiteResponse, summary="Rank Best-Fit Lead Customers for a Site")
def get_leads_for_site(
    site_id: str,
    limit: Optional[int] = Query(None, ge=1, description="Limit number of leads returned"),
    include_disqualified: bool = Query(True, description="Whether to include hard-disqualified customers at bottom"),
    ref_date: Optional[str] = Query("2026-08-08", description="Reference date (YYYY-MM-DD)")
):
    """
    Ranks customers for a specific vacant site using 6 weighted scoring factors.
    Enforces HARD BUDGET CONSTRAINT: Customers whose budget band is 2+ levels below the site rate band
    are hard-disqualified with total_score = 0.
    Every lead includes explicit, human-readable reason strings.
    """
    try:
        hoardings_df, customers_df, bookings_df = load_all_datasets()
        score_data = calculate_lead_scores(
            site_id=site_id,
            hoardings_df=hoardings_df,
            customers_df=customers_df,
            bookings_df=bookings_df,
            reference_date_str=ref_date,
            include_disqualified=include_disqualified
        )

        if limit and limit > 0:
            score_data["leads"] = score_data["leads"][:limit]
            score_data["leads_count"] = len(score_data["leads"])

        return score_data
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error scoring leads for site {site_id}: {str(exc)}")


@app.post("/api/pitch", response_model=PitchResponse, summary="Generate Personalised Pitch Offer")
def generate_pitch_endpoint(
    payload: PitchRequest,
    ref_date: Optional[str] = Query("2026-08-08", description="Reference date (YYYY-MM-DD)")
):
    """
    Generates a personalized B2B sales pitch offer for a lead customer and vacant site.
    Strictly grounded in site location, size, and rate card.
    Uses Anthropic Claude API if ANTHROPIC_API_KEY is configured, or templated generator fallback.
    """
    try:
        hoardings_df, customers_df, bookings_df = load_all_datasets()
        pitch_data = generate_pitch(
            site_id=payload.site_id,
            customer_id=payload.customer_id,
            hoardings_df=hoardings_df,
            customers_df=customers_df,
            bookings_df=bookings_df,
            reference_date_str=ref_date
        )
        return pitch_data
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating pitch: {str(exc)}")
