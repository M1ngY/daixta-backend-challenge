import math
from datetime import date
from decimal import Decimal
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    date: date
    description: str = Field(..., min_length=1, max_length=255)
    amount: Decimal

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("description must not be empty")
        return cleaned

    @field_validator("amount")
    @classmethod
    def amount_finite(cls, value: float | Decimal) -> Decimal:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("amount must be finite (no NaN or Inf)")
        d = Decimal(str(value))
        if d.is_nan() or d.is_infinite():
            raise ValueError("amount must be finite (no NaN or Inf)")
        return d


class AnalyzeRequest(BaseModel):
    transactions: List[Transaction] = Field(..., min_length=1)


class RiskFlag(BaseModel):
    code: str
    message: str
    severity: Literal["low", "medium", "high"]


class FinancialSummary(BaseModel):
    total_inflow: Decimal
    total_outflow: Decimal
    net_cash_flow: Decimal
    inflow_count: int
    outflow_count: int
    largest_inflow: Decimal
    largest_outflow: Decimal
    average_transaction_value: Decimal


class AnalyzeResponse(BaseModel):
    summary: FinancialSummary
    risk_flags: List[RiskFlag]
    readiness: Literal["strong", "structured", "requires_clarification"]