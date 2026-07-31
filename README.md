# Farmitra

Submission for the Synaptrix Hackathon (BMSCE IEEE Computer Society x Protocol)

## Problem Statement Chosen
**Domain:** AgriSense  
**Problem Statement:** How can AI help smallholder farmers in India make better crop-health and market decisions using only a basic smartphone?

## Team
**Team Name:** ZeroDay

## Our Solution

Farmitra is an AI-powered farm companion web app that gives smallholder farmers instant, plain-language guidance directly from their phone. A farmer photographs a diseased crop leaf — Farmitra identifies the disease via HuggingFace Inference API and explains remedies in simple language using OpenAI. It then shows live mandi price trends with a 7-day regression forecast, and an agentic AI advisor checks prices, weather, and storage life together to recommend whether to "Sell Now" or "Hold". The entire flow works end-to-end as a Progressive Web App installable directly to the home screen — no app store required.

## AI Component

**What AI is used:**
- **HuggingFace Inference API** — MobileNetV2 model (`linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification`) pretrained on PlantVillage dataset (54,000 labeled leaf images, 38 disease classes). Called via HTTPS REST API — no local PyTorch/transformers installation required.
- **OpenAI `gpt-4o-mini` via API** — used for all natural language tasks: chatbot explanation of disease diagnosis, and the agentic sell/hold advisor with tool-calling.

**What it does in the app:**
1. **Disease detection:** HuggingFace API classifies uploaded leaf image, returns disease label + confidence score.
2. **Chatbot explanation:** `gpt-4o-mini` receives diagnosis and generates farmer-friendly plain-language explanation plus 2-3 low-cost remedy steps. Farmers can ask follow-up questions by typing or speaking.
3. **Sell/Hold advisor (agentic):** `gpt-4o-mini` is invoked with three callable tools — `get_price_trend`, `get_weather_forecast`, `get_perishability`. The model autonomously calls all three, reasons over combined results, and outputs a recommendation with justification. This is genuine LLM tool-calling, not hardcoded logic. The full reasoning trace is displayed in the UI.

**Why we chose this approach:**
- HuggingFace Inference API removes the need for local GPU/torch installation and eliminates ~2 GB of dependencies — keeping Render deploys fast and free-tier compatible.
- Hosted inference means zero cold-start delay from model loading.
- `gpt-4o-mini` has tool-calling support at the lowest OpenAI cost tier — enabling genuine agentic behavior without breaking the budget.

## Tech Stack

- **Frontend:** React 18 (Vite), plain CSS, PWA (vite-plugin-pwa, service worker, web manifest)
- **Backend:** Python 3.10, FastAPI, uvicorn
- **AI/ML:** HuggingFace Inference API (MobileNetV2 / PlantVillage), OpenAI API (`gpt-4o-mini`), scikit-learn (polynomial regression for price forecasting)
- **Database/Storage:** Synthetic CSV files (simulated mandi price data with seasonal trends) — no database server needed
- **Other tools/APIs:** Open-Meteo (free weather API, no key), Web Speech API (voice input, browser-native), slowapi (rate limiting), Recharts (price trend chart)

## Features Implemented

### Core Requirements
- [x] **Crop disease/pest detection** — `POST /diagnose` — HuggingFace Inference API identifies disease from photo, returns label + confidence score
- [x] **Chatbot explanation** — `POST /explain` — OpenAI generates plain-language explanation + 2-3 remedy steps for non-technical farmers; follow-up questions supported
- [x] **Mandi price trend** — `GET /price-trend?crop=<name>` — 90-day history + 7-day polynomial regression forecast, rendered as interactive line chart
- [x] **Sell/Hold advisor (agentic)** — `POST /advisor` — genuine OpenAI tool-calling with `get_price_trend`, `get_weather_forecast`, `get_perishability`; reasoning trace surfaced in UI
- [x] **Voice input** — browser-native Web Speech API, no external service (works on localhost + HTTPS)
- [x] **PWA / installable** — service worker + web manifest, "Add to Home Screen" on Android

### Bonus Features Attempted
- [ ] Yield-loss estimation — not attempted (scoped out for time)
- [ ] Multi-photo field scan — not attempted (scoped out for time)
- [ ] Community outbreak map — not attempted (scoped out for time)
- [ ] Multilingual support — not attempted (scoped out for time)
- [ ] Community Q&A — not attempted (scoped out for time)

## How to Run This Project

```bash
# Clone the repo
git clone https://github.com/InfoNaveen/Farmitra
cd Farmitra

# --- Backend ---
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Generate synthetic price data (one-time)
python generate_price_data.py

# Copy env file and add your API keys
cp .env.example .env
# Edit .env — set OPENAI_API_KEY=sk-... and HF_API_TOKEN=hf_...

# Start backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# --- Frontend (new terminal) ---
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

> **Windows shortcut:** Double-click `START_BACKEND.bat` and `START_FRONTEND.bat` from the project root.

## Screenshots

_Screenshots showing: (1) Diagnose tab with diagnosis + chatbot explanation, (2) Prices tab with trend chart, (3) Advisor tab with "Sell Now" recommendation + reasoning trace visible._

---

## API Keys / Environment Variables

**Do not hardcode API keys or upload them directly to GitHub.**

1. Create a `.env` file in `backend/` with your keys (see `.env.example` for required variable names: `OPENAI_API_KEY`, `HF_API_TOKEN`, `ALLOWED_ORIGINS`, `RATE_LIMIT_PER_MINUTE`).
2. `.env` is already in `.gitignore` — it will never be pushed.
3. `.env.example` is committed and lists variable names only, no real values.

**Get your keys:**
- OpenAI API key: https://platform.openai.com/api-keys
- HuggingFace token (READ scope only): https://huggingface.co/settings/tokens

## Deployment

### Backend → Render

1. Push repo to GitHub (public)
2. Go to **render.com** → New → Web Service → connect repo → root directory `backend/`
3. Build command: `pip install -r requirements.txt && python generate_price_data.py`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `OPENAI_API_KEY`, `HF_API_TOKEN`, `ALLOWED_ORIGINS` (add your Vercel URL once deployed), `RATE_LIMIT_PER_MINUTE=10`
6. Health check path: `/health`

### Frontend → Vercel

1. **vercel.com** → New Project → import repo → root directory `frontend/`
2. Set environment variable: `VITE_API_URL=https://your-backend.onrender.com`
3. Build command: `npm run build` | Output directory: `dist`

**After both are deployed:** Update `ALLOWED_ORIGINS` in Render environment variables to include your Vercel URL (e.g., `http://localhost:5173,https://farmitra.vercel.app`)

**Cold start note:** Render free tier sleeps after 15 minutes of inactivity. First request after sleep takes ~30 seconds — the frontend shows a "Backend not reachable" banner while waking up.

## Security

All OWASP-aligned hardening applied:
- Startup validation fails fast if API keys missing
- Prompt-injection screening on user text
- Image upload MIME + magic-byte + size validation
- Crop parameter allowlist validation
- Rate limiting (10 req/min/IP, configurable)
- LLM tool-call loop capped at 5 iterations
- CORS locked to `ALLOWED_ORIGINS` env var
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `CSP`
- Structured logging (no PII, no secrets)
- Generic error messages to client; full detail logged server-side only

See `TESTING.md` for manual QA checklist. Run automated tests: `cd backend && python -m pytest tests/ -v` (25 tests, all pass).
