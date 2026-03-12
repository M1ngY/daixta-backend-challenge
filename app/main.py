from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.models import AnalyzeRequest, AnalyzeResponse
from app.analyzer import analyze_transactions

app = FastAPI(
    title = "Daixta Backend Challenge",
    version = "1.0.0",
    description = "Financial transaction analysis service",
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/analyze-file", response_model=AnalyzeResponse)
def analyze_file(payload: AnalyzeRequest) -> AnalyzeResponse:
    return analyze_transactions(payload)
