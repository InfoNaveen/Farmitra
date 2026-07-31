"""
Tests for POST /diagnose
- Valid JPEG → 200 + correct JSON shape
- Valid PNG  → 200 + correct JSON shape
- Invalid MIME type → 400
- File too large → 413
- Non-image bytes with image MIME → 400
"""
import io


def test_diagnose_valid_jpeg(client, valid_jpeg_bytes):
    response = client.post(
        "/diagnose",
        files={"file": ("leaf.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "disease_label" in data
    assert "confidence_score" in data
    assert "top_predictions" in data
    assert isinstance(data["confidence_score"], float)
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert isinstance(data["top_predictions"], list)
    assert len(data["top_predictions"]) > 0
    # Each prediction must have label and score
    for pred in data["top_predictions"]:
        assert "label" in pred
        assert "score" in pred


def test_diagnose_valid_png(client, valid_png_bytes):
    response = client.post(
        "/diagnose",
        files={"file": ("leaf.png", valid_png_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "disease_label" in data
    assert "confidence_score" in data


def test_diagnose_invalid_mime_type(client, valid_jpeg_bytes):
    """PDF MIME type should be rejected with 400."""
    response = client.post(
        "/diagnose",
        files={"file": ("doc.pdf", valid_jpeg_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_diagnose_invalid_mime_text(client):
    """Plain text MIME type should be rejected with 400."""
    response = client.post(
        "/diagnose",
        files={"file": ("notes.txt", b"some text content", "text/plain")},
    )
    assert response.status_code == 400


def test_diagnose_file_too_large(client):
    """Files over 5 MB should be rejected with 413."""
    big_data = b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024 + 1)  # JPEG magic + oversized
    response = client.post(
        "/diagnose",
        files={"file": ("big.jpg", big_data, "image/jpeg")},
    )
    assert response.status_code == 413


def test_diagnose_corrupt_image_bytes(client):
    """Valid MIME but corrupt image bytes should be rejected with 400."""
    fake_jpeg = b"\xff\xd8\xff" + b"\x00" * 100   # valid JPEG magic, corrupt body
    response = client.post(
        "/diagnose",
        files={"file": ("corrupt.jpg", fake_jpeg, "image/jpeg")},
    )
    assert response.status_code == 400


def test_diagnose_label_cleaned(client, valid_jpeg_bytes):
    """Disease label should not contain raw underscores from the model."""
    response = client.post(
        "/diagnose",
        files={"file": ("leaf.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    label = response.json()["disease_label"]
    assert "___" not in label
