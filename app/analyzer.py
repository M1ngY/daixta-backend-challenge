from decimal import Decimal
from statistics import mean

from app.config import (
    LARGE_OUTFLOW_RATIO,
    MAX_RISK_FLAGS_FOR_STRONG,
    MIN_INFLOW_COUNT,
    NSF_KEYWORDS,
)
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    FinancialSummary,
    RiskFlag,
    Transaction,
)


def round_money(value: Decimal | float) -> Decimal:
    return Decimal(str(round(float(value), 2)))


def contains_nsf_keywords(description: str | None) -> bool:
    if not description:
        return False
    normalized = description.lower()
    return any(keyword in normalized for keyword in NSF_KEYWORDS)


def build_summary(transactions: list[Transaction]) -> FinancialSummary:
    inflows = [tx.amount for tx in transactions if tx.amount > 0]
    outflows = [abs(tx.amount) for tx in transactions if tx.amount < 0]
    absolute_values = [abs(tx.amount) for tx in transactions]

    total_inflow = sum(inflows)
    total_outflow = sum(outflows)
    net_cash_flow = total_inflow - total_outflow

    zero = Decimal("0")
    return FinancialSummary(
        total_inflow=round_money(total_inflow),
        total_outflow=round_money(total_outflow),
        net_cash_flow=round_money(net_cash_flow),
        inflow_count=len(inflows),
        outflow_count=len(outflows),
        largest_inflow=round_money(max(inflows)) if inflows else round_money(zero),
        largest_outflow=round_money(max(outflows)) if outflows else round_money(zero),
        average_transaction_value=round_money(mean(absolute_values)) if absolute_values else round_money(zero),
    )


def build_risk_flags(
        transactions: list[Transaction],
        summary: FinancialSummary
) -> list[RiskFlag]:
    risk_flags: list[RiskFlag] = []

    if any(contains_nsf_keywords(tx.description) for tx in transactions):
        risk_flags.append(
            RiskFlag(
                code="NSF_ACTIVITY_DETECTED",
                message="Transaction history includes NSF or overdraft-related activity",
                severity="high",
            )
        )

    zero = Decimal("0")
    if summary.largest_outflow > zero:
        if summary.total_inflow == zero:
            risk_flags.append(
                RiskFlag(
                    code="LARGE_SINGLE_OUTFLOW",
                    message="Outflow activity exists without any recorded inflow",
                    severity="high",
                )
            )
        elif summary.largest_outflow > Decimal(str(LARGE_OUTFLOW_RATIO)) * summary.total_inflow:
            risk_flags.append(
                RiskFlag(
                    code="LARGE_SINGLE_OUTFLOW",
                    message=f"A single outflow exceeds {int(LARGE_OUTFLOW_RATIO * 100)}% of total inflow",
                    severity="medium",
                )
            )
    
    if summary.net_cash_flow < zero:
        risk_flags.append(
            RiskFlag(
                code="NEGATIVE_NET_CASH_FLOW",
                message="Total outflow exceeds total inflow",
                severity="high",
            )
        )
    
    if summary.inflow_count < MIN_INFLOW_COUNT:
        risk_flags.append(
            RiskFlag(
                code="LOW_INFLOW_FREQUENCY",
                message=f"Fewer than {MIN_INFLOW_COUNT} inflow transactions were detected",
                severity="medium",
            )
        )

    return risk_flags


def classify_readiness(
    summary: FinancialSummary,
    risk_flags: list[RiskFlag],
) -> str:
    zero = Decimal("0")
    has_high_risk = any(flag.severity == "high" for flag in risk_flags)

    if summary.inflow_count == 0 or summary.net_cash_flow < zero or has_high_risk:
        return "requires_clarification"

    if (
        summary.net_cash_flow > zero
        and summary.inflow_count >= MIN_INFLOW_COUNT
        and len(risk_flags) <= MAX_RISK_FLAGS_FOR_STRONG
    ):
        return "strong"
    
    return "structured"


def analyze_transactions(payload: AnalyzeRequest) -> AnalyzeResponse:
    summary = build_summary(payload.transactions)
    risk_flags = build_risk_flags(payload.transactions, summary)
    readiness = classify_readiness(summary, risk_flags)

    return AnalyzeResponse(
        summary=summary,
        risk_flags=risk_flags,
        readiness=readiness,
    )