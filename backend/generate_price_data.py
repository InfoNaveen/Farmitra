"""
Script to generate synthetic mandi (agricultural market) price data.
Simulated data — NOT real market prices. Disclosed in README.
Seasonal trends modeled as sinusoidal patterns + Gaussian noise.
"""

import csv
import math
import random
from datetime import date, timedelta

random.seed(42)

CROPS = {
    "tomato": {
        "base_price": 2000,      # Rs per quintal
        "amplitude": 800,        # seasonal swing — highly volatile
        "phase_offset": 1.5,     # peak around month 6 (June)
        "noise_std": 200,
        "trend_per_day": 0.5,
    },
    "wheat": {
        "base_price": 2200,
        "amplitude": 300,
        "phase_offset": 0.0,     # peak around Rabi harvest (April)
        "noise_std": 100,
        "trend_per_day": 0.3,
    },
    "onion": {
        "base_price": 1800,
        "amplitude": 900,        # very volatile — infamous price swings
        "phase_offset": -0.8,    # peaks Oct-Nov (kharif harvest)
        "noise_std": 280,
        "trend_per_day": 0.4,
    },
    "potato": {
        "base_price": 1200,
        "amplitude": 350,        # moderate seasonal variation
        "phase_offset": 0.5,     # peaks around March-April
        "noise_std": 120,
        "trend_per_day": 0.2,
    },
    "rice": {
        "base_price": 3000,
        "amplitude": 150,        # relatively stable — staple grain
        "phase_offset": 2.0,     # slight peak post-kharif (Nov-Dec)
        "noise_std": 80,
        "trend_per_day": 0.35,
    },
}

START_DATE = date(2023, 1, 1)
END_DATE   = date(2026, 7, 30)   # 3.5 years of history


def generate(crop: str, params: dict):
    rows = []
    current = START_DATE
    day_idx  = 0
    while current <= END_DATE:
        month_angle = (2 * math.pi * current.month) / 12
        seasonal    = params["amplitude"] * math.sin(month_angle + params["phase_offset"])
        trend       = params["trend_per_day"] * day_idx
        noise       = random.gauss(0, params["noise_std"])
        price       = max(500, params["base_price"] + seasonal + trend + noise)
        rows.append((current.isoformat(), round(price, 2)))
        current += timedelta(days=1)
        day_idx  += 1
    return rows


if __name__ == "__main__":
    import os
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    for crop, params in CROPS.items():
        rows = generate(crop, params)
        path = os.path.join(out_dir, f"{crop}_prices.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "price_per_quintal"])
            writer.writerows(rows)
        print(f"  Written {len(rows)} rows → {path}")
