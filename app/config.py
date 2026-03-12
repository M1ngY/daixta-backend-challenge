"""
Business rules and tunable parameters for transaction analysis.
"""

# NSF-related keywords (case-insensitive match in transaction descriptions)
NSF_KEYWORDS: frozenset[str] = frozenset({
    "nsf",
    "non-sufficient funds",
    "overdraft",
})

# Single outflow is "large" when it exceeds this fraction of total inflow
LARGE_OUTFLOW_RATIO: float = 0.4

# Minimum number of inflow transactions to avoid LOW_INFLOW_FREQUENCY
MIN_INFLOW_COUNT: int = 2

# Maximum risk flags (with no high severity) to still get "strong" readiness
MAX_RISK_FLAGS_FOR_STRONG: int = 1
