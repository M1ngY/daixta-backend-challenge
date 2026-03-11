from fastapi imoprt FastAPI
from app.models import AnalyzeRequest, AnalyzeResponse
from app.analyzer import analyze_transactions

app = FastAPI(
    title = "Daixta Backend Challenge",
    version = "1.0.0",
    description = "Financial transaction analysis service"
)

@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}

@app.post("/analyze-file", response_model=AnalyzeResponse)
def analyze_file(payload: AnalyzeRequest) -> AnalyzeResponse:
    return analyze_transactions(payload)