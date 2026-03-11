from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_file_success():
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "Salary", "amount": 3000.0},
            {"date": "2026-03-02", "description": "Rent", "amount": -1200.0},
            {"date": "2026-03-03", "description": "Groceries", "amount": -200.0},
            {"date": "2026-03-04", "description": "Side Income", "amount": 500.0},
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["total_inflow"] == 3500.0
    assert body["summary"]["total_outflow"] == 1400
    assert body["summary"]["net_cash_flow"] == 2100.0
    assert body["summary"]["inflow_count"] == 2
    assert body["summary"]["outflow_count"] == 2
    assert body["readiness"] in {"strong", "structured", "requries_clarification"}

def test_analyze_file_detects_nsf():
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "NSF fee", "amount": -35.0}
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 200
    body = response.json()

    risk_codes = [flag["code"] for flag in body["risk_flags"]]
    assert "NSF_ACTIVITY_DETECTED" in risk_codes
    assert body["readiness"] == "requires_clarification"