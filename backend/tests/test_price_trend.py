"""
Tests for GET /price-trend
- Valid crop 'tomato' → 200 + correct JSON shape
- Valid crop 'wheat'  → 200 + correct JSON shape
- Invalid crop        → 400
- Case-insensitive crop names normalised
"""


def test_price_trend_tomato(client):
    response = client.get("/price-trend", params={"crop": "tomato"})
    assert response.status_code == 200
    data = response.json()

    assert data["crop"] == "tomato"
    assert "history" in data
    assert "forecast" in data
    assert "current_price" in data
    assert "trend_direction" in data
    assert "note" in data

    assert isinstance(data["current_price"], float)
    assert data["trend_direction"] in ("rising", "falling", "stable")

    # History should have up to 90 entries
    assert 1 <= len(data["history"]) <= 90
    # Forecast must be exactly 7 days
    assert len(data["forecast"]) == 7

    # Each history row: date + price
    for row in data["history"]:
        assert "date" in row
        assert "price" in row
        assert isinstance(row["price"], float)

    # Each forecast row: date + price
    for row in data["forecast"]:
        assert "date" in row
        assert "price" in row
        assert row["price"] >= 200   # floor applied in regression


def test_price_trend_wheat(client):
    response = client.get("/price-trend", params={"crop": "wheat"})
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "wheat"
    assert len(data["forecast"]) == 7


def test_price_trend_invalid_crop(client):
    """Unknown crop names must be rejected with 400."""
    response = client.get("/price-trend", params={"crop": "mango"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_price_trend_onion(client):
    """Onion should return 200 with correct shape after crop expansion."""
    response = client.get("/price-trend", params={"crop": "onion"})
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "onion"
    assert len(data["forecast"]) == 7
    assert data["current_price"] > 0


def test_price_trend_potato(client):
    response = client.get("/price-trend", params={"crop": "potato"})
    assert response.status_code == 200
    assert response.json()["crop"] == "potato"


def test_price_trend_rice(client):
    response = client.get("/price-trend", params={"crop": "rice"})
    assert response.status_code == 200
    assert response.json()["crop"] == "rice"


def test_price_trend_injection_attempt(client):
    """Injection strings should be rejected by the allowlist."""
    response = client.get(
        "/price-trend",
        params={"crop": "tomato; DROP TABLE prices;"},
    )
    assert response.status_code == 400


def test_price_trend_missing_crop(client):
    """Missing crop param should return 422 (Pydantic/FastAPI validation)."""
    response = client.get("/price-trend")
    assert response.status_code == 422


def test_price_trend_simulated_note(client):
    """Response must include a note disclosing simulated data."""
    response = client.get("/price-trend", params={"crop": "tomato"})
    assert response.status_code == 200
    note = response.json().get("note", "").upper()
    assert "SIMULATED" in note
