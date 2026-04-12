# App Review Lens — Supervisor Pitch

> **One-liner:** App Review Lens is an **automated review intelligence platform** that ingests Google Play Store reviews for food-delivery apps, runs NLP-powered analysis, and surfaces **prioritized, actionable insights** on a PM-grade dashboard — replacing hours of manual review reading with a single glance.

---

## 1. The Problem We Solve

Product managers at food-delivery companies (Swiggy, Zomato, Uber Eats, DoorDash) receive **thousands of reviews daily**. Manually reading them is impossible. Critical issues — a delivery-time regression, a payment bug, a food-quality complaint wave — get buried. By the time the PM notices, the damage (churn, bad ratings) is already done.

**App Review Lens automates the entire feedback loop:**

```
Play Store Reviews  →  Ingest  →  NLP Pipeline  →  Classify  →  Prioritize  →  Alert  →  Dashboard
```

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                       FRONTEND (Angular)                     │
│  Dashboard  ·  Competitor Compare  ·  Issue Drill-Down       │
│  Sentiment Charts  ·  Alert Panel  ·  Filterable Review Table│
└────────────────────────┬─────────────────────────────────────┘
                         │  REST API (JSON)
┌────────────────────────▼─────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                 │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │  Ingestion   │  │  NLP Pipeline │  │  Insights Engine    │ │
│  │  (scraper)   │→ │  (VADER,      │→ │  (classify, rank,   │ │
│  │              │  │   spaCy)      │  │   alert, trend)     │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │  SQLite DB   │  │  Background  │  │  AI Suggestions     │ │
│  │  (SQLAlchemy)│  │  Worker      │  │  (OpenAI GPT)       │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

| Layer | Tech | Role |
|-------|------|------|
| **Frontend** | Angular 16+ (standalone components) | Interactive PM dashboard with charts, filters, drill-down |
| **API** | FastAPI (Python) | REST endpoints for reviews, insights, comparison, AI |
| **NLP** | VADER Sentiment + spaCy | Sentiment scoring, lemmatization, stopword removal |
| **Classification** | Custom keyword ontology (11 categories) | Maps every review to a food-delivery issue category |
| **Prioritization** | Weighted composite scoring | Ranks issues by frequency, sentiment, rating, recency |
| **Alerting** | Spike detection (week-over-week) | Flags 30%+ increases in negative sentiment |
| **Background** | APScheduler | Auto-ingests new reviews every few hours |
| **AI** | OpenAI GPT-3.5/4 | Generates executive summaries, action items, release notes |
| **Storage** | SQLite + SQLAlchemy ORM | Persistent review store with aspect-level sentiment |

---

## 3. How the Data Pipeline Works (End to End)

### Step 1: Review Ingestion

```python
# We scrape Google Play Store using google-play-scraper
reviews_data, _ = fetch_reviews("in.swiggy.android", country="us", count=300)
```

- Uses the `google-play-scraper` library to pull up to 300 newest reviews per app
- Each review gets a **unique hash ID** (prevents duplicates)
- Supports **multi-country, multi-language** ingestion (US, IN, UK, CA, AU)
- A **background worker** (APScheduler) auto-ingests every few hours so the dashboard stays fresh

### Step 2: Text Preprocessing

```
Raw: "Worst app ever!!! food was COLD & delivery took 2 hrs 😡😡😡"
  ↓ clean_text()     → remove URLs, emails, special chars
  ↓ lowercase()      → "worst app ever food was cold delivery took 2 hrs"
  ↓ lemmatize()      → "worst app food cold delivery take hr"  (spaCy lemma + stopword removal)
```

- **spaCy** (`en_core_web_sm`) handles lemmatization and stopword removal
- Falls back to a basic regex + stopword-set approach if spaCy isn't installed
- Also runs **spam detection** to filter out gibberish/bot reviews

### Step 3: Sentiment Analysis (VADER)

This is the core of "how we know if a review is positive or negative."

```python
# VADER produces a compound score from -1.0 (most negative) to +1.0 (most positive)
compound = vader.polarity_scores(text)["compound"]

# We normalize to a 0–1 scale for storage:
normalized_score = (compound + 1) / 2.0
# Examples:
#   "Worst app ever"     → compound = -0.68 → normalized = 0.16 (very negative)
#   "Great food, fast!"  → compound = +0.75 → normalized = 0.87 (very positive)
#   "It's okay"          → compound = +0.02 → normalized = 0.51 (neutral)

# Label thresholds (backend):
#   compound >= 0.05  → "positive"
#   compound <= -0.05 → "negative"
#   else              → "neutral"
```

**Why VADER?**
- Specifically designed for **social media / short informal text** (perfect for app reviews)
- Handles slang, emoji, capitalization, punctuation emphasis ("GREAT!!!" scores higher than "great")
- No training required — works out of the box
- Falls back to a keyword heuristic scorer if VADER isn't installed

**Frontend re-derivation:** The dashboard also re-derives sentiment labels from the 0–1 score to ensure consistency:
```
score < 0.4  → Negative
score > 0.6  → Positive
else         → Neutral
```

### Step 4: Issue Classification (Food Delivery Ontology)

Every review is classified into one of **11 domain-specific categories**:

| Category | Example Keywords | Example Review |
|----------|-----------------|----------------|
| `delivery_time` | late, delay, slow delivery, took too long | "Waited 2 hours for my order" |
| `delivery_agent` | rude driver, delivery boy, tampered | "Driver ate my food" |
| `food_quality` | cold food, stale, hair in food, cockroach | "Food was completely cold and soggy" |
| `order_accuracy` | wrong item, missing, incomplete order | "Got paneer instead of chicken" |
| `packaging` | spilled, leaked, broken seal, torn | "Container was open, food spilled" |
| `app_experience` | crash, bug, slow app, login issue | "App crashes every time I open it" |
| `payment` | refund, double charged, payment failed | "Charged twice, no refund yet" |
| `pricing` | expensive, surge pricing, hidden charges | "Too many hidden platform fees" |
| `promotions_offers` | coupon not working, fake offer | "Promo code never applies" |
| `customer_support` | no response, useless support, bot response | "Support chat is just bots" |
| `restaurant_issue` | restaurant closed, cancelled by restaurant | "Restaurant cancelled after 1 hour" |

**How classification works:**
```python
# 1. Match review text against keyword lists for each category
# 2. Multi-word phrases score HIGHER (weighted by word count)
#    "cold food" (2 words) → score 2.0  vs  "cold" (1 word) → score 1.0
# 3. Highest-scoring category wins
# 4. If no keywords match → check generic fallback words ("food" → food_quality, "deliver" → delivery_time)
# 5. Only if nothing matches → "uncategorized"
```

### Step 5: Severity Scoring

Each review gets a **severity score (0–10)** combining three signals:

```
Severity = 0.40 × Rating Component      ← 1-star = max severity
         + 0.35 × Sentiment Component   ← lower sentiment = higher severity
         + 0.25 × Keyword Intensity     ← "worst", "scam", "disgusting" = amplified

Example:
  1-star + sentiment 0.15 + "worst terrible disgusting" →
  0.40 × 1.0 + 0.35 × 0.85 + 0.25 × 0.6 = 0.40 + 0.30 + 0.15 = 0.85 → Severity 8.5/10
```

### Step 6: Issue Prioritization (How Top Issues Are Ranked)

This is the key output — **what should the PM fix first?**

Reviews are **grouped by category**, then each category gets a **priority score (0–100)**:

```
Priority Score = 0.40 × Frequency        ← How many reviews mention this issue
               + 0.30 × Sentiment        ← How negative are they (inverted)
               + 0.20 × Rating           ← Average star rating (lower = higher priority)
               + 0.10 × Recency          ← Recent issues rank higher

Example — "delivery_time" with 45 mentions, avg sentiment 0.25, avg rating 1.8, 3 days old:
  Frequency:  min(45/50, 1.0) = 0.90
  Sentiment:  (0.5 - 0.25) × 2 = 0.50
  Rating:     (5 - 1.8) / 5 = 0.64
  Recency:    1 - (3/30) = 0.90
  
  Priority = 0.40×0.90 + 0.30×0.50 + 0.20×0.64 + 0.10×0.90
           = 0.36 + 0.15 + 0.128 + 0.09 = 0.728 → Score: 72.8 / 100
```

The dashboard then **filters to only show issues with avg_sentiment < 0.4** (genuinely negative) and sorts by priority score descending. This ensures PMs see the most urgent, most complained-about issues at the top.

### Step 7: Alert Generation (Spike Detection)

The system compares **this week vs last week** for negative review volume:

```
Last week: 12 negative reviews about "payment"
This week: 20 negative reviews about "payment"
Change:    (20 - 12) / 12 = 66.7% increase  →  🚨 ALERT (threshold: 30%)

Alert: "Payment issues increased 67% this week (12 → 20)"
Severity: "critical" if change > 50%, "high" if > 30%
```

Alerts fire for:
- **Overall** negative sentiment spikes
- **Per-category** spikes (e.g., sudden surge in "delivery_time" complaints)
- **New wave** detection (0 → many negative reviews in a category)

---

## 4. Frontend Dashboard Features

### Main Dashboard (Single-Page Layout)
1. **App Selector** — Switch between Swiggy, Zomato, Uber Eats, Instamart
2. **Summary Cards** — Total reviews, avg rating, sentiment distribution at a glance
3. **Alert Panel** — Real-time spike notifications with severity badges
4. **Sentiment Chart** — Visual breakdown of positive / negative / neutral
5. **Top Issues List** — Prioritized issues ranked by composite score, clickable for drill-down
6. **Review Table** — Filterable by sentiment, rating, time period; shows review text, rating, sentiment label, category, date

### Issue Drill-Down
- Click any top issue → see all reviews in that category
- Sentiment trend over time for that specific issue
- Sample reviews with severity scores

### Competitor Comparison
- Side-by-side aspect-level sentiment comparison across 2+ apps
- Shows which app is winning/losing on delivery, food quality, support, etc.

### AI Suggestions (GPT-Powered)
- Feed top issues + trends to GPT → get:
  - **Executive summary** ("Delivery time complaints spiked 40% this week...")
  - **Action items** ("Investigate courier allocation algorithm...")
  - **Suggested release notes** ("Fixed delivery ETA accuracy...")
  - **A/B test ideas** ("Experiment: Show live courier location...")

### Filters
- **Time period**: 7 / 14 / 30 / 90 days
- **Rating**: 1–5 stars
- **Sentiment**: positive / negative / neutral
- Filters apply across all views (issues, reviews, charts)

---

## 5. Key Technical Decisions & Why

| Decision | Why |
|----------|-----|
| **VADER over ML model** | Zero training needed, excellent on short informal text (reviews), handles emoji/slang. For a V1 this gives 85%+ accuracy without GPU costs |
| **Keyword classification over ML** | Transparent, debuggable, no training data needed. PM can understand exactly why a review was classified as "delivery_time". Easy to extend with new keywords |
| **Weighted multi-word scoring** | "slow delivery" (2 words) matching is a stronger signal than just "slow" alone. Reduces miscategorization |
| **Fallback chain everywhere** | VADER → keyword heuristic; spaCy → basic regex; ensures app works even with minimal dependencies |
| **0–1 normalized sentiment** | Universal scale. Backend stores one number, frontend/backend can independently derive labels with consistent thresholds |
| **Background worker** | Reviews auto-refresh. PM doesn't need to manually trigger ingestion — dashboard is always current |
| **Standalone Angular components** | Modern Angular pattern, tree-shakeable, no NgModule boilerplate |

---

## 6. What Makes This Different

1. **Domain-specific ontology** — Not generic sentiment analysis. Built specifically for food-delivery pain points (delivery time, packaging, rider behavior, etc.)
2. **Composite prioritization** — Doesn't just count complaints. Weighs frequency × negativity × rating × recency to surface what actually matters
3. **Proactive alerting** — Week-over-week spike detection catches regressions before they snowball
4. **Actionable, not just analytical** — AI-generated action items turn data into decisions
5. **Competitor benchmarking** — Know if your delivery-time sentiment is worse than Zomato's

---

## 7. Data Flow Summary (TL;DR)

```
Google Play Store
       │
       ▼
  ┌─────────────────┐
  │  Scrape Reviews  │  (google-play-scraper, 300/app, multi-country)
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  Preprocess Text │  (clean → lowercase → lemmatize via spaCy)
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │  Spam Detection  │  (filter out bots & gibberish)
  └────────┬────────┘
           ▼
  ┌─────────────────────────────────────────────────┐
  │                NLP Analysis                      │
  │  ┌───────────┐ ┌─────────────┐ ┌──────────────┐ │
  │  │ Sentiment │ │ Classify    │ │ Severity     │ │
  │  │ (VADER)   │ │ (11-cat     │ │ (0-10 score) │ │
  │  │ → 0-1     │ │  ontology)  │ │              │ │
  │  └───────────┘ └─────────────┘ └──────────────┘ │
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │              SQLite Database                     │
  │  Reviews table: text, rating, sentiment,         │
  │  sentiment_score, category, severity, timestamp  │
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │           Insights Engine                        │
  │  ┌──────────────┐ ┌─────────┐ ┌──────────────┐  │
  │  │ Prioritize   │ │ Alerts  │ │ Trends       │  │
  │  │ (rank issues │ │ (spike  │ │ (daily/weekly │  │
  │  │  by impact)  │ │  detect)│ │  sentiment)  │  │
  │  └──────────────┘ └─────────┘ └──────────────┘  │
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │           Angular Dashboard                      │
  │  Top Issues · Alerts · Charts · Review Table     │
  │  Filters · Competitor Compare · AI Suggestions   │
  └─────────────────────────────────────────────────┘
```

---

## 8. Talking Points for the Presentation

### Opening (30 seconds)
> "Imagine you're a PM at Swiggy. You get 5,000 reviews a day. Which ones matter? App Review Lens reads every single review, understands what users are complaining about, scores how severe each issue is, and tells you exactly what to fix first — automatically, every day."

### Demo Flow (suggested)
1. **Show the dashboard** — Point out summary cards, sentiment chart
2. **Show Top Issues** — "These are ranked by a composite of frequency, negativity, rating, and recency. Delivery time is #1 because 45 people complained this week with avg 1.8 stars."
3. **Click into an issue** — Show the drill-down with individual reviews
4. **Show the Alerts panel** — "This flagged a 67% spike in payment complaints. Without this, we'd have found out from Twitter."
5. **Show Competitor Compare** — "Swiggy's delivery sentiment is 0.3 vs Zomato's 0.5 — we're losing on delivery."
6. **Show the Review table with filters** — Filter by 1-star + negative → see the worst reviews instantly
7. **Explain the pipeline** — Use the data flow diagram above

### Closing (15 seconds)
> "Right now this handles 4 food-delivery apps. The architecture is modular — swap the keyword ontology and it works for any app vertical. Next steps: ML-based classification, real-time streaming, and Slack/Teams alert integration."

---

## 9. Quick Reference: Formulas

| What | Formula | Scale |
|------|---------|-------|
| **Sentiment Score** | `(VADER compound + 1) / 2` | 0 (negative) → 1 (positive) |
| **Sentiment Label** | `< 0.4` = negative, `> 0.6` = positive, else neutral | — |
| **Severity** | `0.40 × rating + 0.35 × sentiment + 0.25 × keywords` | 0–10 |
| **Priority** | `0.40 × frequency + 0.30 × sentiment + 0.20 × rating + 0.10 × recency` | 0–100 |
| **Alert Threshold** | Week-over-week negative count change > 30% | — |
| **Classification** | Max weighted keyword score; multi-word phrases score higher | 11 categories |
