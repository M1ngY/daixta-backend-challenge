from statistics import mean

from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    FinancialSummary,
    RiskFlag,
    Transaction,
)

NSF_KEYWORDS = {"nsf", "non-sufficient funds", "overdraft"}

def round_money(value: float) -> float:
    return round(value, 2)

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

    return FinancialSummary(
        total_inflow=round_money(total_inflow),
        total_outflow=round_money(total_outflow),
        net_cash_flow=round_money(net_cash_flow),
        inflow_count=len(inflows),
        outflow_count=len(outflows),
        largest_inflow=round_money(max(inflows) if inflows else 0.0),
        largest_outflow=round_money(max(outflows) if outflows else 0.0),
        average_transaction_value=round_money(mean(absolute_values)) if absolute_values else 0.0,
    )

def build_risk_flags(
        transactions: list[Transaction],
        summary: FinancialSummary
) -> list[RiskFlag]:
    risk_flags: list[RiskFlag] = {}

    if any(contains_nsf_keywords(tx.description) for tx in transactions):
        risk_flags.append(
            RiskFlag(
                code = "NSF_ACTIVITY_DETECTED",
                message = "Transaction history includes NSF or overdraft-related activity",
                severity = "high",
            )
        )
    
    if summary.largest_outflow > 0:
        if summary.total_inflow == 0:
            risk_flags.append(
                RiskFlag(
                    code = "LARGE_SINGLE_OUTFLOW",
                    message = "Outflow activity exists without any recorded inflow",
                    severity = "high",
                )
            )
        elif summary.largest_outflow > 0.4 * summary.total_inflow:
            risk_flags.append(
                RiskFlag(
                    code = "LARGE_SINGLE_OUTFLOW",
                    message = "A single outflow exceeds 40% of total inflow",
                    severity = "medium",
                )
            )
    
    if summary.net_cash_flow < 0:
        risk_flags.append(
                RiskFlag(
                    code = "NEGATIVE_NET_CASH_FLOW",
                    message = "Total outflow exceeds total inflow",
                    severity = "high",
                )
            )
    
    if summary.inflow_count < 2:
        risk_flags.append(
            RiskFlag(
                    code = "LOW_INFLOW_FREQUENCY",
                    message = "Fewer than two inflow transactions were detected",
                    severity = "medium",
                )
        )

    return risk_flags

def classify_readiness(
        summary: FinancialSummary,
        risk_flags: list[RiskFlag]
) -> str:
    has_high_risk = any(flag.severity == "high" for flag in risk_flags)

    if summary.inflow_count == 0 or summary.net_cash_flow < 0 or has_high_risk:
        return "requires_clarification"
    
    if (
        summary.net_cash_flow > 0
        and summary.inflow_count >= 2
        and len(risk_flags) <= 1
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