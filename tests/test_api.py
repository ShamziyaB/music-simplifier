import base64
from pathlib import Path

from fastapi.testclient import TestClient

from app import app

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "piano_sample.musicxml"
client = TestClient(app)


def _payload(level: str = "easy", filename: str = "piano_sample.musicxml") -> dict:
    return {
        "filename": filename,
        "level": level,
        "content_base64": base64.b64encode(SAMPLE.read_bytes()).decode("ascii"),
    }


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_levels_payload():
    response = client.get("/api/levels")
    assert response.status_code == 200
    keys = [item["key"] for item in response.json()["levels"]]
    assert keys == ["easy", "medium", "medium_hard"]


def test_simplify_easy():
    response = client.post("/api/simplify", json=_payload("easy"))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["level"] == "easy"
    assert data["level_label"] == "Легко"
    assert "score-partwise" in data["musicxml"] or "score-timewise" in data["musicxml"]
    assert data["midi_base64"]
    assert "ОТЧЁТ ОБ УПРОЩЕНИИ" in data["report"]
    assert data["stats"]["chord_reductions"] >= 1
    assert data["validation"]["ok"] is True


def test_simplify_unknown_level():
    response = client.post("/api/simplify", json=_payload("very_hard"))
    assert response.status_code == 400
    assert "уровень" in response.json()["detail"].lower()


def test_simplify_bad_extension():
    response = client.post("/api/simplify", json=_payload(filename="notes.pdf"))
    assert response.status_code == 400
    assert "формат" in response.json()["detail"].lower()


def test_simplify_bad_base64():
    payload = _payload()
    payload["content_base64"] = "not base64!"
    response = client.post("/api/simplify", json=payload)
    assert response.status_code == 400
