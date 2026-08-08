# Smart Leads Agent for Hoardings - Backend

An AI-powered out-of-home (OOH) media sales lead generation engine built for hoarding billboard owners. It automatically detects upcoming billboard site vacancies, scores best-fit corporate lead customers using a multi-factor transparent algorithm, and generates personalized sales pitch proposals.

---

## Key Features

1. **90-Day Vacancy Detection Pipeline**
   - Scans booking schedules to detect sites falling vacant within the next 90 days (`[today, today + 90 days]`).
   - Calculates exact `free_from` availability date (`end_date + 1 day`).
   - Automatically filters out sites with follow-on bookings or contracts extending beyond 90 days.

2. **Transparent 6-Factor Lead Scoring Engine**
   - **Hard Budget Constraint (Disqualification Rule):** Disqualifies any customer whose budget band (`low`/`mid`/`high`) is 2+ levels below the site's rate band (`low`/`mid`/`high`). Low budget customers cannot appear at the top of high-rate premium sites.
   - **6 Weighted Scoring Factors:**
     1. **Site History (25 pts):** Previous bookings at this exact location.
     2. **Overall Booking History (15 pts):** Repeat client relationship across network.
     3. **Budget Band Fit (20 pts):** Alignment with rate card.
     4. **Industry Fit (20 pts):** Inferred from historical occupant industry profiles for the specific site.
     5. **Relationship Score (10 pts):** Account strength (1–10 scale).
     6. **Recency of Contact (10 pts):** Active sales dialogue recency.
   - **Explicit Human-Readable Reasons:** Every lead carries concrete, data-backed reasons explaining why this customer is recommended for this site (no black-box scores).
   - **Incumbent Renewal Tracking:** Flags incumbent occupants for proactive renewal outreach.

3. **Grounded Sales Pitch Generator**
   - Generates B2B sales email pitches strictly grounded in verified dataset facts (location, size, rate in INR, eyeball traffic score).
   - Integrates with the **Anthropic Claude API** when `ANTHROPIC_API_KEY` is provided.
   - Seamlessly falls back to a template-driven dynamic pitch engine if no API key is present.

---

## Dataset Schema (`backend/data/`)

- `hoardings.csv`: `site_id`, `location`, `size_sqft`, `traffic_score`, `monthly_rate_inr` (25 sites, rate range ₹120,000–400,000/month).
- `customers.csv`: `customer_id`, `name`, `industry`, `budget_band` (`low`/`mid`/`high`), `relationship_score` (1–10), `last_contact_date`.
- `bookings.csv`: `booking_id`, `site_id`, `customer_id`, `start_date`, `end_date`, `value_inr`.

---

## API Endpoints

### 1. `GET /api/vacancies`
Detects upcoming vacant hoardings ending in the next 90 days.

- **Query Parameters:**
  - `max_days` *(int, default: 90)*: Lookahead window in days.
  - `ref_date` *(string, default: "2026-08-08")*: Reference evaluation date (`YYYY-MM-DD`).

- **Sample Response:**
```json
[
  {
    "site_id": "SITE_001",
    "location": "Bandra Flyover Junction - SV Road",
    "size_sqft": 800,
    "traffic_score": 9.5,
    "monthly_rate_inr": 380000,
    "rate_band": "high",
    "end_date": "2026-08-31",
    "free_from": "2026-09-01",
    "days_until_vacant": 24,
    "current_occupant_id": "CUST_001",
    "current_occupant_name": "Raymond Lifestyle Ltd"
  }
]
```

---

### 2. `GET /api/leads/{site_id}`
Returns ranked best-fit customer leads for a given vacant site.

- **Query Parameters:**
  - `limit` *(int, optional)*: Max number of leads to return.
  - `include_disqualified` *(bool, default: true)*: Include hard-disqualified customers at bottom.
  - `ref_date` *(string, default: "2026-08-08")*: Reference date.

- **Sample Response:**
```json
{
  "site_id": "SITE_001",
  "location": "Bandra Flyover Junction - SV Road",
  "monthly_rate_inr": 380000,
  "rate_band": "high",
  "leads_count": 30,
  "leads": [
    {
      "customer_id": "CUST_001",
      "customer_name": "Raymond Lifestyle Ltd",
      "industry": "Retail",
      "budget_band": "high",
      "relationship_score": 9,
      "last_contact_date": "2026-08-01",
      "total_score": 93.0,
      "is_disqualified": false,
      "disqualification_reason": null,
      "breakdown": {
        "site_history": 25.0,
        "total_history": 10.0,
        "budget_fit": 20.0,
        "industry_fit": 20.0,
        "relationship": 9.0,
        "contact_recency": 9.0
      },
      "reasons": [
        "CURRENT INCUMBENT: Currently occupying SITE_001 — prime renewal candidate before site opens to market!",
        "Strong site history: Booked this exact location (Bandra Flyover Junction - SV Road) 2 times previously.",
        "Budget alignment: Customer budget band ('high') matches/exceeds site rate (₹380,000/month - 'high').",
        "Proven industry fit: 'Retail' is a proven top occupant industry for this location (3 past bookings)."
      ],
      "incumbent_status": true
    }
  ]
}
```

---

### 3. `POST /api/pitch`
Generates a grounded, high-converting personalized B2B pitch proposal.

- **Request Body:**
```json
{
  "site_id": "SITE_001",
  "customer_id": "CUST_001"
}
```

- **Sample Response:**
```json
{
  "site_id": "SITE_001",
  "customer_id": "CUST_001",
  "site_location": "Bandra Flyover Junction - SV Road",
  "customer_name": "Raymond Lifestyle Ltd",
  "quoted_rate_inr": 380000,
  "pitch_text": "Dear Raymond Lifestyle Ltd Team,\n\nWe value our ongoing partnership with your brand...\n\n### Key Site Specifications (Verified Rate Card):\n- Location: Bandra Flyover Junction - SV Road\n- Display Size: 800 sq. ft.\n- Traffic Rating: 9.5/10 High-Density Eyeball Score\n- Monthly Rate: ₹380,000 / month (Fixed Rate Card)\n...",
  "generated_by_ai": false,
  "grounding_facts": {
    "site_id": "SITE_001",
    "location": "Bandra Flyover Junction - SV Road",
    "size_sqft": 800,
    "traffic_score": 9.5,
    "monthly_rate_inr": 380000,
    "customer_name": "Raymond Lifestyle Ltd"
  }
}
```

---

### 4. `GET /api/health`
Health check endpoint reporting API status and loaded dataset row counts.

---

## Local Setup & Testing

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run API Server
```bash
python -m uvicorn app.main:app --reload --app-dir backend
```
Access interactive API docs at `http://127.0.0.1:8000/docs`.

### 3. Run Automated Tests
```bash
PYTHONPATH=backend pytest backend/tests -v
```