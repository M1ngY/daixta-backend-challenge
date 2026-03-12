import math

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models import Transaction

client = TestClient(app)


def _num(value):
    """Normalize JSON number (may be int, float, or string from Decimal)."""
    return float(value) if value is not None else 0.0


def test_analyze_file_success():
    """Healthy payload: two inflows, positive net flow, no high risk -> strong."""
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

    assert _num(body["summary"]["total_inflow"]) == 3500.0
    assert _num(body["summary"]["total_outflow"]) == 1400.0
    assert _num(body["summary"]["net_cash_flow"]) == 2100.0
    assert body["summary"]["inflow_count"] == 2
    assert body["summary"]["outflow_count"] == 2
    assert _num(body["summary"]["largest_inflow"]) == 3000.0
    assert _num(body["summary"]["largest_outflow"]) == 1200.0
    assert body["readiness"] == "strong"
    assert len(body["risk_flags"]) == 0


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


def test_analyze_file_empty_transactions_rejected():
    """Empty transactions list must return 422."""
    response = client.post("/analyze-file", json={"transactions": []})

    assert response.status_code == 422


def test_analyze_file_missing_transactions_key_rejected():
    response = client.post("/analyze-file", json={})

    assert response.status_code == 422


def test_analyze_file_invalid_date_rejected():
    payload = {
        "transactions": [
            {"date": "not-a-date", "description": "Salary", "amount": 1000.0}
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 422


def test_analyze_file_empty_description_rejected():
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "   ", "amount": 1000.0}
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 422


def test_transaction_amount_nan_rejected():
    """Amount must be finite; NaN is rejected by model validator (JSON cannot send nan)."""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(date="2026-03-01", description="Salary", amount=float("nan"))
    assert "amount" in str(exc_info.value).lower() or "finite" in str(exc_info.value).lower()


def test_transaction_amount_inf_rejected():
    """Amount must be finite; Inf is rejected by model validator."""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(date="2026-03-01", description="Salary", amount=math.inf)
    assert "amount" in str(exc_info.value).lower() or "finite" in str(exc_info.value).lower()


def test_analyze_file_all_outflow():
    """Only outflows -> negative net flow, no inflow -> requires_clarification."""
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "Rent", "amount": -1000.0},
            {"date": "2026-03-02", "description": "Bills", "amount": -200.0},
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert _num(body["summary"]["total_inflow"]) == 0.0
    assert _num(body["summary"]["total_outflow"]) == 1200.0
    assert _num(body["summary"]["net_cash_flow"]) == -1200.0
    assert body["summary"]["inflow_count"] == 0
    assert body["readiness"] == "requires_clarification"

    risk_codes = [f["code"] for f in body["risk_flags"]]
    assert "NEGATIVE_NET_CASH_FLOW" in risk_codes
    assert "LOW_INFLOW_FREQUENCY" in risk_codes
    assert "LARGE_SINGLE_OUTFLOW" in risk_codes


def test_analyze_file_single_large_outflow():
    """One outflow > 40% of total inflow -> LARGE_SINGLE_OUTFLOW medium."""
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "Salary", "amount": 1000.0},
            {"date": "2026-03-02", "description": "Big payment", "amount": -500.0},
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert _num(body["summary"]["total_inflow"]) == 1000.0
    assert _num(body["summary"]["largest_outflow"]) == 500.0

    risk_codes = [f["code"] for f in body["risk_flags"]]
    assert "LARGE_SINGLE_OUTFLOW" in risk_codes
    # Still positive net flow and 2 inflows; one medium flag -> structured
    assert body["readiness"] == "structured"


def test_analyze_file_negative_net_cash_flow():
    """Outflow > inflow -> NEGATIVE_NET_CASH_FLOW, requires_clarification."""
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "Salary", "amount": 500.0},
            {"date": "2026-03-02", "description": "Rent", "amount": -1200.0},
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert _num(body["summary"]["net_cash_flow"]) == -700.0
    assert body["readiness"] == "requires_clarification"

    risk_codes = [f["code"] for f in body["risk_flags"]]
    assert "NEGATIVE_NET_CASH_FLOW" in risk_codes


def test_analyze_file_low_inflow_frequency():
    """Only one inflow -> LOW_INFLOW_FREQUENCY, readiness not strong."""
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "Salary", "amount": 3000.0},
            {"date": "2026-03-02", "description": "Rent", "amount": -500.0},
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["inflow_count"] == 1
    risk_codes = [f["code"] for f in body["risk_flags"]]
    assert "LOW_INFLOW_FREQUENCY" in risk_codes
    assert body["readiness"] == "structured"


def test_analyze_file_readiness_structured():
    """Two inflows, positive net, but two risk flags -> structured."""
    payload = {
        "transactions": [
            {"date": "2026-03-01", "description": "Salary", "amount": 1000.0},
            {"date": "2026-03-02", "description": "Big expense", "amount": -500.0},
        ]
    }

    response = client.post("/analyze-file", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["readiness"] == "structured"
    assert len(body["risk_flags"]) >= 2


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
