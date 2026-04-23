# App Review Lens

**Actionable review insights for product teams.**

App Review Lens fetches live Google Play Store reviews and transforms them into categorized issues, sentiment scores, severity ratings, and prioritized "what to fix now" insights — all displayed in an interactive Angular dashboard.

---

## Quick Start

### Prerequisites

| Tool       | Version  |
|------------|----------|
| Python     | 3.10+    |
| Node.js    | 18+      |
| npm        | 9+       |

### 1. Clone & Setup Backend

```bash
cd app-review-lens

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Install VADER sentiment model
pip install vaderSentiment

# (Optional) Install spaCy for advanced preprocessing
pip install spacy && python -m spacy download en_core_web_sm
```

### 2. Setup Frontend

```bash
cd frontend
npm install
```

### 3. Run the App

Open **two terminals**:

**Terminal 1 — Backend** (runs on http://localhost:8000):
```bash
cd app-review-lens
source .venv/bin/activate
cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend** (runs on http://localhost:4200):
```bash
cd app-review-lens/frontend
npx ng serve --port 4200
```

Open **http://localhost:4200** in your browser.

---

## How to Use

### Step 1: Select an App

The dashboard comes pre-configured with popular food delivery apps (Swiggy, Zomato, Uber Eats). Select one from the dropdown at the top.

### Step 2: Ingest Reviews

Click **"📥 Ingest Reviews"** to fetch the latest reviews from the Google Play Store. This pulls live reviews, runs them through the processing pipeline, and stores them in the database.

### Step 3: Explore the Dashboard

Once reviews are ingested, the dashboard loads automatically with two tabs:

#### Overview Tab

| Section | What It Shows |
|---------|---------------|
| **Summary Cards** | Current rating, rating trend (improving/declining/stable), total reviews, and the top issue |
| **Alerts Panel** | Spike alerts — e.g. *"Delivery delays increased 40% this week"* — color-coded by severity (red = critical, orange = high, yellow = medium, green = low) |
| **Charts** | Rating trend line chart + issue distribution bar chart |
| **Sentiment Distribution** | Pie chart showing positive / negative / neutral split |
| **Issue Prioritization Table** | Ranked list of issues with impact score, trend direction (↑ worsening, ↓ improving, → stable), affected user %, average rating, and severity |

#### Reviews Tab

Browse all ingested reviews with columns for date, rating, sentiment, issue category, severity score, and text. Use the **"View All"** button to expand.

### Step 4: Apply Filters

Use the filter bar to narrow data by:
- **Time range**: 7 / 14 / 30 / 90 days
- **Rating**: 1★ through 5★
- **Sentiment**: Positive / Neutral / Negative

Filters apply to both the Overview and Reviews tabs.

### Step 5: Drill Into Issues

Click any row in the **Issue Prioritization Table** to open the **Issue Detail Page**, which shows:

| Section | Description |
|---------|-------------|
| **Summary Cards** | Affected users %, average rating, severity, and total mentions for this specific issue |
| **Sentiment Breakdown Bar** | Visual split of positive / neutral / negative reviews within this issue |
| **Trend Chart** | Dual-axis line chart showing sentiment trend and negative review count over time |
| **AI Insight Box** | Auto-generated insight like *"Users are strongly dissatisfied with delivery time, affecting 16.7% of reviews. Complaints are concentrated around version 4.106.1."* |
| **Review List** | Individual reviews with keyword highlighting (words like "late", "cold", "crash" are highlighted in yellow) |

### Step 6: Compare Apps

Click **"📊 Compare Apps"** from the dashboard to compare two apps side by side on aspects and issues.

---

## Features

### Issue Classification (6 Categories)

Every review is automatically classified into one of these food delivery categories:

| Category | Examples |
|----------|----------|
| `delivery_time` | Late delivery, long wait, delayed |
| `food_quality` | Cold food, stale, undercooked |
| `order_accuracy` | Wrong item, missing item |
| `app_experience` | App crash, bugs, slow loading |
| `payment` | Refund issues, double charged |
| `customer_support` | No response, unhelpful support |

### Sentiment Analysis

Uses **VADER** (Valence Aware Dictionary and sEntiment Reasoner) to score every review from 0 (most negative) to 1 (most positive), with labels: positive, neutral, or negative.

### Severity Scoring (0–10)

Each review gets a composite severity score based on:
- **Rating** (40% weight) — lower star rating = higher severity
- **Sentiment** (35% weight) — more negative = higher severity
- **Negative keywords** (25% weight) — words like "worst", "never", "scam"

### Prioritization Engine

Reviews are aggregated by issue category and ranked by a weighted **impact score**:
- 50% frequency (how many reviews mention this issue)
- 30% average severity
- 20% negative sentiment ratio

### Spike Alerts

The system compares the last 7 days against the previous 7 days. If negative reviews for any category increase by more than 30%, an alert is generated.

---

## API Endpoints

### V2 Insights (Primary)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v2/insights/{app_id}?days=30` | Top issues, alerts, rating trend |
| `GET` | `/v2/insights/{app_id}/issues/{issue_name}?days=30` | Detailed stats for one issue |
| `GET` | `/v2/insights/{app_id}/alerts?days=14` | Active spike alerts |

### Reviews

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reviews/ingest/{app_id}?count=100` | Fetch & process reviews from Play Store |
| `GET` | `/reviews/app/{app_id}/list?limit=50` | List reviews with filters |
| `GET` | `/reviews/app/{app_id}/stats` | Sentiment distribution stats |
| `GET` | `/reviews/app/{app_id}/trends?days=30` | Sentiment trends over time |

### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/compare/sentiment?apps=app1,app2` | Compare sentiment across apps |
| `POST` | `/insights/generate/{app_id}` | Generate V1 insights |
| `GET` | `/policy/responsible-ai` | Active Responsible AI controls and policy manifest |

Full API docs available at **http://localhost:8000/docs** (Swagger UI) when the backend is running.

---

## Responsible AI Policy (Implemented)

The backend now enforces privacy-first Responsible AI controls by default:

- **PII scrubbing on ingest**: emails, phone numbers, payment-like numbers, UPI handles, IPs, and order IDs are redacted from review text before storage.
- **Pseudonymized authors**: reviewer names are pseudonymized by default.
- **Raw payload minimization**: raw provider payload storage is disabled by default to reduce retention risk.
- **PII-safe LLM prompting**: payloads are scrubbed before they are sent to LLM endpoints.
- **Policy transparency endpoint**: current active controls are visible via `/policy/responsible-ai`.

Environment flags:

- `RAI_PII_SCRUB=true|false`
- `RAI_SCRUB_EMAIL=true|false`
- `RAI_SCRUB_PHONE=true|false`
- `RAI_SCRUB_CARD=true|false`
- `RAI_SCRUB_UPI=true|false`
- `RAI_SCRUB_IP=true|false`
- `RAI_SCRUB_ORDER_ID=true|false`
- `RAI_STORE_RAW_PAYLOAD=true|false` (default: false)
- `RAI_STORE_AUTHOR=true|false` (default: false)
- `RAI_LLM_SCRUB=true|false`

---

## Project Structure

```
app-review-lens/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── reviews.py           # Review ingest & list endpoints
│   │   │   ├── insights_v2.py       # V2 insights endpoints
│   │   │   ├── insights.py          # V1 insights
│   │   │   ├── compare.py           # App comparison
│   │   │   └── ai.py                # AI-powered endpoints
│   │   ├── services/
│   │   │   ├── preprocessing.py     # Text cleaning & lemmatization
│   │   │   ├── classification.py    # Issue classification (6 categories)
│   │   │   ├── sentiment.py         # VADER sentiment analysis
│   │   │   ├── severity.py          # Severity scoring (0-10)
│   │   │   ├── prioritization.py    # Issue ranking & impact scores
│   │   │   ├── alerts.py            # Spike detection
│   │   │   ├── trends.py            # Trend calculations
│   │   │   ├── nlp.py               # V1 NLP utilities
│   │   │   └── playstore_scraper.py # Google Play Store scraper
│   │   ├── models/
│   │   │   ├── review.py            # SQLAlchemy models
│   │   │   └── insight.py           # Insight models
│   │   └── db/
│   │       ├── base.py              # DB base
│   │       └── session.py           # DB session
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── src/app/
│   │   ├── dashboard/               # Main dashboard (overview + reviews tabs)
│   │   ├── components/
│   │   │   ├── summary-card/        # Rating, trend, top issue cards
│   │   │   ├── issue-list/          # Prioritized issue table
│   │   │   ├── issue-detail/        # Issue deep-dive page
│   │   │   ├── alerts/              # Alert cards panel
│   │   │   ├── charts/              # Chart.js rating trend + issue bar charts
│   │   │   ├── filters/             # Time, rating, sentiment filters
│   │   │   └── sentiment-chart.component.ts  # Pie chart
│   │   ├── compare/                 # App comparison page
│   │   ├── services/
│   │   │   ├── api.service.ts       # All HTTP calls to backend
│   │   │   └── compare.service.ts   # Compare-specific calls
│   │   ├── models/
│   │   │   └── insights.model.ts    # TypeScript interfaces
│   │   ├── app-routing.module.ts    # Routes
│   │   └── app.component.ts         # Root component
│   ├── angular.json
│   └── package.json
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, FastAPI, SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| Frontend | Angular 16, Chart.js, TypeScript |
| Sentiment | VADER (vaderSentiment) |
| Preprocessing | spaCy (optional, falls back to basic tokenization) |
| Data Source | Google Play Store (via google-play-scraper) |

---

## Color Coding Guide

Throughout the app, colors indicate severity and status:

| Color | Meaning | Used For |
|-------|---------|----------|
| 🔴 Red | Critical / Bad | Severity > 7, rating < 2, "worsening" trends |
| 🟠 Orange | High / Warning | Severity 5–7, medium-priority alerts |
| 🟡 Yellow | Medium | Severity 3–5, moderate issues |
| 🟢 Green | Good / Low | Severity < 3, rating ≥ 4, "improving" trends |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'google_play_scraper'` | Run `pip install google-play-scraper` in your venv |
| `vaderSentiment not installed, using keyword fallback` | Run `pip install vaderSentiment` — the app works without it but VADER is more accurate |
| `spaCy not available, falling back to basic preprocessing` | Optional — run `pip install spacy && python -m spacy download en_core_web_sm` |
| `Port 8000 already in use` | Kill the old process: `lsof -ti:8000 \| xargs kill -9` |
| `Port 4200 already in use` | Kill the old process: `lsof -ti:4200 \| xargs kill -9` |
| Database schema errors after update | Delete `backend/app.db` and restart the backend — tables auto-create on startup |
