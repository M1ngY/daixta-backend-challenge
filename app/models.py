from datetime import date
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

class Transaction(BaseModel):
    date: date
    description: str = Field(..., min_length=1, max_length=255)
    amount: float

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("description must not be empty")
        return cleaned

class AnalyzeRequest(BaseModel):
    transactions: List[transaction] = Field(..., min_length=1)

class RiskFlag(BaseModel):
    code: str
    message: str
    severity: Literal["low", "medium", "high"]

class FinancialSummary(BaseModel):
    total_inflow: float
    total_outflow: float
    net_cash_flow: float
    inflow_count: int
    outflow_count: int
    largest_inflow: float
    largest_outflow: float
    average_transaction_value: float

class AnalyzeResponse(BaseModel):
    summary: FinancialSummary
    risk_flags: List[RiskFlag]
    readiness: Literal["strong", "structured", "requires_clarification"]