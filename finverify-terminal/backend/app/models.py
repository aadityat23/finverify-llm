"""
Pydantic Models
===============
Request / response schemas for the FastAPI endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str = Field(..., description="Financial question to ask the LLM")
    context: Optional[str] = Field(None, description="Optional additional context")


class VerifyRequest(BaseModel):
    question: str = Field(..., description="Financial question (for DVL keyword detection)")
    raw_number: float = Field(..., description="Raw number to verify through the DVL")


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class CorrectionEntry(BaseModel):
    rule: str
    before: float
    after: float
    description: str


class QueryResponse(BaseModel):
    question: str
    raw_text: Optional[str] = None
    raw_number: Optional[float] = None
    verified_number: Optional[float] = None
    correction_log: list[CorrectionEntry] = []
    trust_score: str = "HIGH"
    trust_color: str = "#00ff88"
    display_value: str = "N/A"
    mode: str = "numerical"          # "numerical" | "advisory" | "general"
    verified: bool = True            # whether DVL verification was applied


class HealthResponse(BaseModel):
    status: str = "ok"
    model: str = "aadi2026/finverify-lora"


class SampleQuery(BaseModel):
    question: str
    actual: Optional[float] = None
    category: Optional[str] = None
