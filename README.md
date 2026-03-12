# Daixta Backend Challenge

A **Financial Transaction Analysis Service** that accepts a list of transactions, computes a financial summary, risk flags, and a readiness classification.

---

## Quick Start

### Run locally

```bash
# Python 3.11+ recommended
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for Swagger API documentation.

### Docker

```bash
docker build -t daixta-backend .
docker run -p 8000:8000 daixta-backend
```

### Tests

```bash
pytest
```

---

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Redirects to `/docs` |
| GET | `/health` | Health check; returns `{"status": "ok"}` |
| POST | `/analyze-file` | Submit transaction list; returns analysis result |

**Request body example** (`/analyze-file`):

```json
{
  "transactions": [
    { "date": "2026-03-01", "description": "Salary", "amount": 3000.0 },
    { "date": "2026-03-02", "description": "Rent", "amount": -1200.0 }
  ]
}
```

**Response**: includes `summary` (financial summary), `risk_flags` (list of risk flags), and `readiness` (`strong` / `structured` / `requires_clarification`).

---

## Assumptions and Logic

### Data assumptions

- **Amount sign**: Positive amounts are inflows; negative amounts are outflows. In the summary, `total_outflow` and `largest_outflow` use absolute values.
- **Description**: Required, trimmed of leading/trailing whitespace, must be non-empty, max length 255; used for risk detection (e.g. NSF keywords).
- **Date**: Stored as a transaction attribute only; the current logic does not sort by time or apply time-window analysis; all transactions contribute equally to aggregates and risk rules.

### Financial summary logic

- **total_inflow / total_outflow**: Sum of all positive / negative amounts (outflows as absolute values).
- **net_cash_flow**: `total_inflow - total_outflow`.
- **inflow_count / outflow_count**: Number of transactions with positive / negative amounts.
- **largest_inflow / largest_outflow**: Single largest inflow / outflow (outflow as largest absolute value).
- **average_transaction_value**: Mean of absolute transaction amounts.
- All monetary fields are rounded to two decimal places.

### Risk flag logic

1. **NSF_ACTIVITY_DETECTED** (severity: high)  
   Added if any transaction’s `description` (case-insensitive) contains `nsf`, `non-sufficient funds`, or `overdraft`.

2. **LARGE_SINGLE_OUTFLOW**  
   - If there is any outflow and **no inflow at all**: add with severity high.  
   - Otherwise, if **largest single outflow > 40% of total inflow**: add with severity medium.

3. **NEGATIVE_NET_CASH_FLOW** (high)  
   Added when net cash flow is negative (total outflow > total inflow).

4. **LOW_INFLOW_FREQUENCY** (medium)  
   Added when inflow count is fewer than 2.

### Readiness logic

- **requires_clarification**: Assigned if any of the following holds  
  - Inflow count is 0  
  - Net cash flow < 0  
  - Any risk flag has severity high  

- **strong**: Assigned when all of the following hold  
  - Net cash flow > 0  
  - Inflow count ≥ 2  
  - Number of risk flags ≤ 1 (and none with severity high)  

- **structured**: Assigned when the case is neither strong nor requires_clarification (e.g. has inflows, non-negative net cash flow, no high-severity risks, but more than one risk flag or other conditions that don’t meet strong).

---

## If you had four more hours to improve this service, what would you change and why?

With four extra hours, I would focus on:

1. **Observability and operations**  
   - Add request/response logging (with optional sanitization), latency, and error rates for `/analyze-file` to aid debugging and monitoring.  
   - Add or document a health check and a simple metrics endpoint (e.g. request count) in Docker/deployment for future Prometheus or APM integration.

2. **Input validation and error messages**  
   - Stricter validation for `date` and `amount` (e.g. date range, disallow NaN/Inf), with clear 422 responses and field-level error messages.  
   - Enforce a limit or pagination for very large payloads (e.g. > 10k transactions) to avoid overload.

3. **Security and performance**  
   - Add rate limiting (by IP or API key) to reduce abuse.  
   - If analysis becomes heavier, consider async jobs (e.g. Celery/Redis) or caching of identical requests with a TTL.

4. **Risk rules and configurability**  
   - Move NSF keywords, the 40% threshold, and readiness rules into configuration (env vars or config file) so different environments or clients can tune without code changes.  
   - Add unit tests and edge cases for risk rules so changes can be regression-tested.

5. **Documentation and delivery**  
   - Document `requirements.txt` and minimum Python version in the README.  
   - Ensure the Dockerfile CMD points to the correct module (e.g. `app.main:app`) and document how to pass environment variables (port, log level, etc.).

Overall, the four hours would go into observability, validation, and configuration so the service is easier to operate, safer, and easier to evolve.
