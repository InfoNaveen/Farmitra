"""
Shared pytest fixtures for Farmitra backend tests.
The OpenAI client and HF Inference API are mocked so tests never consume real API credits.
"""
import io
import os
import types
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

# ── Ensure env vars are set before importing main ──────────────────────────
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fakekeyfortesting")
os.environ.setdefault("HF_API_TOKEN", "hf_test_faketoken")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "100")  # high limit for tests


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient with HF Inference API and OpenAI patched out."""
    from unittest.mock import patch, MagicMock, AsyncMock

    # Patch HF Inference API call
    async def mock_hf_classify(image_bytes):
        return [
            {"label": "Tomato___Early_blight", "score": 0.91},
            {"label": "Tomato___Late_blight",  "score": 0.06},
            {"label": "Tomato___healthy",       "score": 0.03},
        ]

    # Patch OpenAI client
    mock_openai = MagicMock()
    _make_choice = lambda content: types.SimpleNamespace(
        choices=[types.SimpleNamespace(
            message=types.SimpleNamespace(content=content, tool_calls=None)
        )]
    )
    mock_openai.return_value.chat.completions.create.return_value = _make_choice(
        "Your crop has a fungal disease.\n"
        "1. Remove affected leaves.\n"
        "2. Apply copper-based fungicide.\n"
        "3. Improve air circulation.\n"
        "RECOMMENDATION: Sell Now\n"
        "Prices are rising and rain is expected. Sell quickly before quality drops."
    )

    with (
        patch("main.classify_image_hf", side_effect=mock_hf_classify),
        patch("main.get_openai_client", return_value=mock_openai.return_value),
    ):
        from main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture
def valid_jpeg_bytes():
    """Minimal valid JPEG image as bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(100, 150, 80))
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def valid_png_bytes():
    """Minimal valid PNG image as bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(100, 150, 80))
    img.save(buf, format="PNG")
    return buf.getvalue()
