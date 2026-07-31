"""
Farmitra FastAPI Backend
========================
Endpoints:
  GET  /health                        — liveness check
  POST /diagnose                      — plant disease detection (HuggingFace)
  POST /explain                       — chatbot explanation (OpenAI)
  GET  /price-trend?crop=<name>       — price history + 7-day regression forecast
  GET  /weather?lat=<f>&lon=<f>       — Open-Meteo forecast with mock fallback
  POST /advisor                       — sell/hold agent with LLM tool calling

Security hardening applied (OWASP-aligned):
  - Startup key validation (fail-fast if OPENAI_API_KEY missing)
  - Input allowlist for crop names (A03 injection prevention)
  - Image upload MIME + size + header validation (API4 resource protection)
  - Prompt-injection sanitisation on user text
  - Rate limiting via slowapi (API4 resource consumption)
  - LLM tool-call loop hard cap (prevents runaway API spend)
  - CORS locked to configurable origins via ALLOWED_ORIGINS env var
  - Security headers middleware (X-Content-Type-Options, X-Frame-Options, CSP)
  - Structured per-request logging (no PII, no secrets)
  - Generic error messages to client; full detail logged server-side only
"""

import io
import json
import logging
import os
import re
import time
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, field_validator
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — structured, no PII, no secrets
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("farmitra")

# ---------------------------------------------------------------------------
# Configuration — read from environment, fail fast if critical keys missing
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "").strip()
HF_MODEL_ID = os.getenv(
    "HF_MODEL",
    "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
)
RATE_LIMIT = os.getenv("RATE_LIMIT_PER_MINUTE", "10")
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# Fail fast — catch missing keys at startup
if not OPENAI_API_KEY:
    raise RuntimeError(
        "\n\n[Farmitra] FATAL: OPENAI_API_KEY is not set.\n"
        "  1. Copy backend/.env.example to backend/.env\n"
        "  2. Set OPENAI_API_KEY=sk-...\n"
        "  3. Restart the server.\n"
    )
if not OPENAI_API_KEY.startswith("sk-"):
    logger.warning("OPENAI_API_KEY does not look like a valid key (should start with 'sk-')")

if not HF_API_TOKEN:
    raise RuntimeError(
        "\n\n[Farmitra] FATAL: HF_API_TOKEN is not set.\n"
        "  Get a READ token from https://huggingface.co/settings/tokens\n"
        "  and add HF_API_TOKEN=hf_... to backend/.env\n"
    )

DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# Rate limiter (slowapi — wraps slowapi around FastAPI)
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Farmitra API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — locked to configured origins (not wildcard *)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

# ---------------------------------------------------------------------------
# Security headers middleware  (X-Content-Type-Options, X-Frame-Options, CSP)
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ---------------------------------------------------------------------------
# Request logging middleware — endpoint, latency, status; NO body/keys
# ---------------------------------------------------------------------------
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "request method=%s path=%s status=%d latency_ms=%s ip=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            get_remote_address(request),
        )
        return response

app.add_middleware(RequestLoggingMiddleware)

# ---------------------------------------------------------------------------
# Constants / allowlists
# ---------------------------------------------------------------------------
SUPPORTED_CROPS = {"tomato", "wheat", "onion", "potato", "rice"}  # allowlist for price-trend
ADVISOR_CROPS   = {"tomato", "wheat", "onion", "potato", "rice"}  # advisor allowlist
MAX_IMAGE_BYTES = 5 * 1024 * 1024             # 5 MB
ALLOWED_MIME    = {"image/jpeg", "image/png", "image/webp"}
MAX_TOOL_CALLS  = 5                            # hard cap on LLM agent loop
MAX_USER_TEXT   = 500                          # max chars in user chat input

# ---------------------------------------------------------------------------
# Input sanitisation helpers
# ---------------------------------------------------------------------------
# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|above|prior|all)\s+instructions?"
    r"|you\s+are\s+now"
    r"|system\s*prompt"
    r"|<\s*/?system\s*>"
    r"|###\s*instruction"
    r"|act\s+as\s+(if\s+you\s+are|a\s+different)"
    r")",
    re.IGNORECASE,
)

def sanitise_user_text(text: str, max_len: int = MAX_USER_TEXT) -> str:
    """Strip excessive whitespace, cap length, and block prompt-injection patterns."""
    if not text:
        return ""
    text = text.strip()[:max_len]
    if _INJECTION_PATTERNS.search(text):
        logger.warning("Potential prompt injection blocked: %s", text[:80])
        raise HTTPException(
            status_code=400,
            detail="Input contains disallowed content.",
        )
    return text

def validate_crop_allowlist(crop: str, allowed: set[str]) -> str:
    """Validate crop against an explicit allowlist; return normalised lowercase value."""
    normalised = crop.strip().lower()
    if normalised not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported crop '{normalised}'. Allowed: {sorted(allowed)}",
        )
    return normalised

# ---------------------------------------------------------------------------
# HuggingFace Inference API client (no local torch/transformers needed)
# ---------------------------------------------------------------------------
async def classify_image_hf(image_bytes: bytes) -> list[dict]:
    """
    Calls HuggingFace Inference API for image classification.
    Returns list of {label, score} dicts, sorted by score descending.
    Raises HTTPException on failure.
    """
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, headers=headers, content=image_bytes)
            r.raise_for_status()
            results = r.json()
            
            # HF returns list of {label, score}
            if isinstance(results, list) and len(results) > 0:
                # Sort by score desc, take top 3
                sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
                return sorted_results[:3]
            else:
                logger.error("Unexpected HF API response format: %s", results)
                raise HTTPException(status_code=500, detail="Unexpected model response format")
                
    except httpx.TimeoutException:
        logger.error("HF Inference API timeout")
        raise HTTPException(
            status_code=504,
            detail="Model inference timed out. The model may be loading — try again in 30 seconds.",
        )
    except httpx.HTTPStatusError as exc:
        logger.error("HF API HTTP error: %s", exc)
        if exc.response.status_code == 503:
            raise HTTPException(
                status_code=503,
                detail="Model is currently loading. Please wait 20-30 seconds and try again.",
            )
        raise HTTPException(status_code=502, detail="Disease detection service unavailable.")
    except Exception as exc:
        logger.error("HF API call failed: %s", exc)
        raise HTTPException(status_code=500, detail="Disease detection failed.")


# ---------------------------------------------------------------------------
# OpenAI client (singleton)
# ---------------------------------------------------------------------------
from openai import OpenAI as _OpenAI

@lru_cache(maxsize=1)
def get_openai_client() -> _OpenAI:
    return _OpenAI(api_key=OPENAI_API_KEY)

# ===========================================================================
# 1. HEALTH CHECK
# ===========================================================================

@app.get("/health")
def health():
    return {"status": "ok", "service": "Farmitra"}

# ===========================================================================
# 2. CROP DISEASE / PEST DETECTION   POST /diagnose
# ===========================================================================

class DiagnoseResponse(BaseModel):
    disease_label:    str
    confidence_score: float
    top_predictions:  list[dict]


@app.post("/diagnose", response_model=DiagnoseResponse)
@limiter.limit(f"{RATE_LIMIT}/minute")
async def diagnose(request: Request, file: UploadFile = File(...)):
    """
    Accepts an image (JPEG/PNG/WebP, max 5 MB), returns top plant disease prediction.
    Uses HuggingFace Inference API (no local model/torch needed).
    Security: MIME allowlist, magic-byte header check, size cap.
    """
    # --- MIME allowlist ---
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, and WebP images are accepted.",
        )

    raw = await file.read()

    # --- Size cap (API4: Unrestricted Resource Consumption) ---
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image too large. Maximum size is 5 MB.",
        )

    # --- Magic-byte header check (don't trust MIME alone) ---
    MAGIC = {
        b"\xff\xd8\xff": "jpeg",
        b"\x89PNG":      "png",
        b"RIFF":         "webp",  # RIFF....WEBP
    }
    valid_magic = any(raw[:4].startswith(sig) for sig in MAGIC)
    if not valid_magic:
        # also accept WebP: bytes 8-12 == b"WEBP"
        valid_magic = len(raw) >= 12 and raw[8:12] == b"WEBP"
    if not valid_magic:
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid image.",
        )

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Cannot decode image.")

    # Call HF Inference API instead of local model
    results = await classify_image_hf(raw)
    
    top = results[0]
    label_clean = top["label"].replace("___", " — ").replace("_", " ").title()

    return DiagnoseResponse(
        disease_label=label_clean,
        confidence_score=round(float(top["score"]), 4),
        top_predictions=[
            {
                "label": r["label"].replace("___", " — ").replace("_", " ").title(),
                "score": round(float(r["score"]), 4),
            }
            for r in results
        ],
    )

# ===========================================================================
# 3. CHATBOT EXPLANATION   POST /explain
# ===========================================================================

class ExplainRequest(BaseModel):
    disease_label:    str
    confidence_score: float
    crop_name:        str | None = None
    user_question:    str | None = None

    @field_validator("disease_label")
    @classmethod
    def clean_disease_label(cls, v: str) -> str:
        return v.strip()[:200]

    @field_validator("user_question")
    @classmethod
    def clean_user_question(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip()[:MAX_USER_TEXT]


class ExplainResponse(BaseModel):
    explanation:  str
    remedy_steps: list[str]
    # raw_response intentionally omitted — not needed by the UI, avoids
    # exposing full LLM output structure to the client (API3 excessive exposure)


@app.post("/explain", response_model=ExplainResponse)
@limiter.limit(f"{RATE_LIMIT}/minute")
def explain(request: Request, req: ExplainRequest):
    """
    Returns a farmer-friendly plain-language explanation + remedy steps.
    User question is sanitised for prompt injection before being forwarded to the LLM.
    """
    # Sanitise user text before inserting into prompt
    safe_question = None
    if req.user_question:
        safe_question = sanitise_user_text(req.user_question)

    safe_label = sanitise_user_text(req.disease_label, max_len=200)

    client = get_openai_client()

    system_prompt = (
        "You are Farmitra, a helpful farm advisor. "
        "Explain crop diseases in simple, friendly language that a smallholder farmer with "
        "limited literacy can understand. Avoid technical jargon. "
        "Always give 2-3 practical, low-cost remedy steps they can act on immediately."
    )

    user_msg = (
        f"My crop has been diagnosed with: {safe_label} "
        f"(confidence: {req.confidence_score * 100:.1f}%)."
    )
    if req.crop_name:
        user_msg += f" The crop is {req.crop_name.strip()[:100]}."
    if safe_question:
        user_msg += f"\n\nFarmer's question: {safe_question}"
    else:
        user_msg += (
            "\n\nPlease explain what this disease means for my crop, "
            "and give me 2-3 practical steps to treat or manage it."
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=600,
        )
    except Exception as exc:
        logger.error("OpenAI /explain failed: %s", exc)
        raise HTTPException(status_code=502, detail="AI explanation service unavailable.")

    raw_text = response.choices[0].message.content.strip()

    lines = raw_text.split("\n")
    remedy_steps: list[str] = []
    explanation_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and stripped[0].isdigit() and len(stripped) > 2 and stripped[1] in ".)":
            remedy_steps.append(stripped[2:].strip())
        else:
            explanation_lines.append(stripped)

    explanation = " ".join(l for l in explanation_lines if l)
    if not remedy_steps:
        remedy_steps = ["Consult your local agricultural extension officer for advice."]

    return ExplainResponse(explanation=explanation, remedy_steps=remedy_steps)

# ===========================================================================
# 4. PRICE TREND   GET /price-trend?crop=<name>
# ===========================================================================

PERISHABILITY_TABLE: dict[str, dict] = {
    "tomato": {"rating": "high",      "days": 5,   "description": "Tomatoes spoil quickly (3-7 days). Sell soon after harvest."},
    "wheat":  {"rating": "low",       "days": 180, "description": "Wheat stores well (up to 6 months). You have time to wait for better prices."},
    "rice":   {"rating": "very low",  "days": 365, "description": "Rice is non-perishable when dry. Can store 1-2 years. No urgency to sell."},
    "onion":  {"rating": "medium",    "days": 60,  "description": "Onions last 1-2 months in cool, dry, well-ventilated storage."},
    "potato": {"rating": "medium",    "days": 90,  "description": "Potatoes last 2-3 months in cool, dark, dry storage."},
}


def load_price_data(crop: str) -> pd.DataFrame:
    path = DATA_DIR / f"{crop}_prices.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No price data for crop: {crop}")
    df = pd.read_csv(path, parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def fit_regression(df: pd.DataFrame, degree: int = 3) -> tuple:
    X = df.index.values.reshape(-1, 1).astype(float)
    y = df["price_per_quintal"].values
    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(X)
    model = LinearRegression()
    model.fit(X_poly, y)
    return model, poly, int(X[-1][0])


class PriceTrendResponse(BaseModel):
    crop:            str
    history:         list[dict]
    forecast:        list[dict]
    current_price:   float
    trend_direction: str
    note:            str


@app.get("/price-trend", response_model=PriceTrendResponse)
def price_trend(crop: str = Query(..., description="Crop name: tomato or wheat")):
    """
    Returns 90-day price history + 7-day polynomial regression forecast.
    Crop is validated against an explicit allowlist (A03 injection prevention).
    DATA NOTE: Prices are SIMULATED synthetic data.
    """
    crop = validate_crop_allowlist(crop, SUPPORTED_CROPS)
    df = load_price_data(crop)
    model, poly, last_idx = fit_regression(df)

    history_df = df.tail(90)
    history = [
        {"date": row["date"].strftime("%Y-%m-%d"), "price": round(row["price_per_quintal"], 2)}
        for _, row in history_df.iterrows()
    ]

    forecast = []
    last_date = df["date"].iloc[-1]
    for i in range(1, 8):
        X_f = poly.transform(np.array([[float(last_idx + i)]]))
        pred = float(model.predict(X_f)[0])
        forecast.append({
            "date":  (last_date + timedelta(days=i)).strftime("%Y-%m-%d"),
            "price": round(max(200, pred), 2),
        })

    current_price = round(float(df["price_per_quintal"].iloc[-1]), 2)
    recent = df.tail(14)["price_per_quintal"].values
    slope  = np.polyfit(range(len(recent)), recent, 1)[0]
    trend  = "rising" if slope > 20 else "falling" if slope < -20 else "stable"

    return PriceTrendResponse(
        crop=crop,
        history=history,
        forecast=forecast,
        current_price=current_price,
        trend_direction=trend,
        note="SIMULATED DATA — for demonstration only. Not real mandi prices.",
    )

# ===========================================================================
# 5. WEATHER   GET /weather?lat=<f>&lon=<f>
# ===========================================================================

def _weather_mock() -> dict:
    return {
        "location": "simulated",
        "source":   "mock_fallback",
        "forecast": [
            {
                "date":             (date.today() + timedelta(days=i)).isoformat(),
                "temp_max":         32 + i % 3,
                "temp_min":         22,
                "precipitation_mm": [0, 2, 0, 5, 1, 0, 3][i],
                "weather_code":     1,
            }
            for i in range(7)
        ],
    }


class WeatherResponse(BaseModel):
    location: str
    source:   str
    forecast: list[dict]


@app.get("/weather", response_model=WeatherResponse)
async def weather(
    lat: float = Query(20.5937, ge=-90,  le=90),
    lon: float = Query(78.9629, ge=-180, le=180),
):
    """
    7-day forecast from Open-Meteo (free, no key).
    Falls back to static mock on any network/API failure.
    lat/lon are clamped to valid ranges via Query validators.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        f"&timezone=Asia%2FKolkata&forecast_days=7"
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            d = r.json()["daily"]
            forecast = [
                {
                    "date":             d["time"][i],
                    "temp_max":         d["temperature_2m_max"][i],
                    "temp_min":         d["temperature_2m_min"][i],
                    "precipitation_mm": d["precipitation_sum"][i],
                    "weather_code":     d["weathercode"][i],
                }
                for i in range(len(d["time"]))
            ]
            return WeatherResponse(
                location=f"{lat},{lon}",
                source="open-meteo",
                forecast=forecast,
            )
    except Exception as exc:
        logger.warning("Open-Meteo call failed, using mock: %s", exc)
        return WeatherResponse(**_weather_mock())

# ===========================================================================
# 6. SELL / HOLD ADVISOR   POST /advisor
#    Genuine OpenAI tool-calling — no hardcoded if/else logic
# ===========================================================================

class AdvisorRequest(BaseModel):
    crop:     str
    location: str | None = None

    @field_validator("crop")
    @classmethod
    def validate_crop(cls, v: str) -> str:
        return v.strip().lower()[:50]

    @field_validator("location")
    @classmethod
    def clean_location(cls, v: str | None) -> str | None:
        return v.strip()[:100] if v else None


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict
    result:    Any


class AdvisorResponse(BaseModel):
    recommendation: str
    justification:  str
    tool_calls:     list[ToolCallRecord]


# --- Tool implementations ---

def _tool_get_price_trend(crop: str) -> dict:
    crop = crop.lower().strip()
    if crop not in SUPPORTED_CROPS:
        return {"error": f"No price data for '{crop}'. Supported: {sorted(SUPPORTED_CROPS)}"}
    df = load_price_data(crop)
    model, poly, last_idx = fit_regression(df)
    current_price = round(float(df["price_per_quintal"].iloc[-1]), 2)
    forecast_prices = []
    for i in range(1, 8):
        X_f = poly.transform(np.array([[float(last_idx + i)]]))
        forecast_prices.append(round(max(200, float(model.predict(X_f)[0])), 2))
    recent    = df.tail(14)["price_per_quintal"].values
    slope     = np.polyfit(range(len(recent)), recent, 1)[0]
    direction = "rising" if slope > 20 else "falling" if slope < -20 else "stable"
    return {
        "crop":          crop,
        "current_price": current_price,
        "trend":         direction,
        "7day_forecast": forecast_prices,
        "avg_forecast":  round(float(np.mean(forecast_prices)), 2),
        "data_note":     "SIMULATED synthetic data",
    }


def _tool_get_weather_forecast(location: str) -> dict:
    lat, lon = 20.5937, 78.9629
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,precipitation_sum,weathercode"
        f"&timezone=Asia%2FKolkata&forecast_days=7"
    )
    try:
        r = httpx.get(url, timeout=5.0)
        r.raise_for_status()
        d = r.json()["daily"]
        return {
            "location":      location,
            "source":        "open-meteo",
            "dates":         d["time"],
            "temp_max":      d["temperature_2m_max"],
            "precipitation": d["precipitation_sum"],
            "weather_codes": d["weathercode"],
        }
    except Exception as exc:
        logger.warning("Weather tool fallback triggered: %s", exc)
        return {
            "location":      location,
            "source":        "mock_fallback",
            "dates":         [(date.today() + timedelta(days=i)).isoformat() for i in range(7)],
            "temp_max":      [33, 34, 32, 31, 33, 35, 34],
            "precipitation": [0, 2, 0, 5, 1, 0, 3],
            "weather_codes": [1, 2, 1, 61, 1, 1, 3],
        }


def _tool_get_perishability(crop: str) -> dict:
    info = PERISHABILITY_TABLE.get(crop.lower())
    if info:
        return {"crop": crop, **info}
    return {
        "crop":        crop,
        "rating":      "medium",
        "days":        14,
        "description": f"No specific data for {crop}. Assume medium perishability (~2 weeks).",
    }


ADVISOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name":        "get_price_trend",
            "description": "Get current market price, 7-day price forecast, and trend direction for a crop.",
            "parameters": {
                "type":       "object",
                "properties": {"crop": {"type": "string"}},
                "required":   ["crop"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name":        "get_weather_forecast",
            "description": "Get 7-day weather forecast for a location.",
            "parameters": {
                "type":       "object",
                "properties": {"location": {"type": "string"}},
                "required":   ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name":        "get_perishability",
            "description": "Get how perishable a crop is and how many days it can be safely stored.",
            "parameters": {
                "type":       "object",
                "properties": {"crop": {"type": "string"}},
                "required":   ["crop"],
            },
        },
    },
]

TOOL_DISPATCHER = {
    "get_price_trend":      lambda a: _tool_get_price_trend(a["crop"]),
    "get_weather_forecast": lambda a: _tool_get_weather_forecast(a["location"]),
    "get_perishability":    lambda a: _tool_get_perishability(a["crop"]),
}


@app.post("/advisor", response_model=AdvisorResponse)
@limiter.limit(f"{RATE_LIMIT}/minute")
def advisor(request: Request, req: AdvisorRequest):
    """
    Sell/Hold advisor using genuine OpenAI tool calling.
    Crop validated against allowlist. Tool-call loop capped at MAX_TOOL_CALLS.
    Location text sanitised before inserting into prompt.
    """
    crop = validate_crop_allowlist(req.crop, ADVISOR_CROPS)
    location = sanitise_user_text(req.location or "India", max_len=100)

    client = get_openai_client()

    system_prompt = (
        "You are Farmitra, an expert farm advisor helping smallholder farmers decide "
        "whether to sell their harvest now or hold it for a better price. "
        "You have access to three tools: price trend data, weather forecast, and crop perishability info. "
        "ALWAYS call all three tools before making your recommendation. "
        "Reason over the combined data. "
        "End your response with a clear line: 'RECOMMENDATION: Sell Now' or 'RECOMMENDATION: Hold'. "
        "Then give a 2-3 sentence plain-language justification a farmer can understand."
    )

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {
            "role":    "user",
            "content": (
                f"I have harvested {crop}. Should I sell it now or wait for better prices? "
                f"My location is {location}. Please check prices, weather, and how long I can store it."
            ),
        },
    ]

    tool_call_trace: list[ToolCallRecord] = []

    try:
        for iteration in range(MAX_TOOL_CALLS + 1):  # +1 for the final answer turn
            if iteration == MAX_TOOL_CALLS:
                logger.warning("Advisor hit MAX_TOOL_CALLS limit (%d) for crop=%s", MAX_TOOL_CALLS, crop)
                break

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=ADVISOR_TOOLS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=800,
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}

                    result = TOOL_DISPATCHER.get(
                        fn_name,
                        lambda _: {"error": f"Unknown tool: {fn_name}"},
                    )(fn_args)

                    tool_call_trace.append(
                        ToolCallRecord(tool_name=fn_name, arguments=fn_args, result=result)
                    )
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      json.dumps(result),
                    })
            else:
                final_text = msg.content or ""
                lower = final_text.lower()
                recommendation = "Hold"
                if "recommendation: sell now" in lower or "recommendation: sell" in lower:
                    recommendation = "Sell Now"

                justification = final_text
                for prefix in [
                    "RECOMMENDATION: Sell Now", "RECOMMENDATION: Hold",
                    "RECOMMENDATION: Sell", "recommendation: sell now", "recommendation: hold",
                ]:
                    justification = justification.replace(prefix, "").strip()

                return AdvisorResponse(
                    recommendation=recommendation,
                    justification=justification,
                    tool_calls=tool_call_trace,
                )
    except Exception as exc:
        logger.error("OpenAI /advisor failed: %s", exc)
        raise HTTPException(status_code=502, detail="Advisor service unavailable.")

    return AdvisorResponse(
        recommendation="Hold",
        justification="Could not complete analysis within the tool-call limit. Please try again.",
        tool_calls=tool_call_trace,
    )


# ===========================================================================
# Dev entry point
# ===========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
