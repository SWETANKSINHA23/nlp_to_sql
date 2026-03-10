from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai
from typing import Optional
import logging
import asyncio
import time
from config import settings
from google.api_core import exceptions as google_exceptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Gemini setup ──────────────────────────────────────────────────────────────
# Model: gemini-2.5-flash-preview-04-17 (aka gemini-2.5-flash-lite)
# Free tier: 15 RPM, 1,000 RPD — the highest available on free tier.
# DO NOT switch to gemini-2.5-flash (only 250 RPD) or gemini-2.0-flash.
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel(
    model_name=settings.model_name,
    generation_config={
        "temperature": settings.temperature,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": settings.max_tokens,
    }
)

# ── Proactive rate limiter (token bucket) ─────────────────────────────────────
# Limits calls to 10 RPM (safely under the 15 RPM free limit).
# This prevents 429 errors before they reach the Gemini API.
_RATE_LIMIT_RPM = 10          # safe cap — well below free-tier 15 RPM
_MIN_INTERVAL   = 60.0 / _RATE_LIMIT_RPM   # seconds between calls
_last_call_time: float = 0.0
_rate_lock = asyncio.Lock()

async def _acquire_rate_limit_slot():
    """Ensure we never exceed 10 RPM by waiting if needed."""
    global _last_call_time
    async with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_call_time
        if elapsed < _MIN_INTERVAL:
            wait = _MIN_INTERVAL - elapsed
            logger.info(f"Rate limiter: waiting {wait:.1f}s before Gemini call")
            await asyncio.sleep(wait)
        _last_call_time = time.monotonic()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="SQL Query Generator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prompt helpers ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert SQL query generator. Convert natural language to valid SQL.
Rules:
- Generate ONLY the SQL query, no explanations or markdown
- Use syntax specific to the target database
- Include proper WHERE, JOIN, GROUP BY clauses as needed
- Use appropriate aggregations (SUM, AVG, COUNT)
- Return the raw SQL query only, no code fences"""

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    schema: Optional[str] = Field(default=None)
    database_type: str = Field(default="PostgreSQL")

class QueryResponse(BaseModel):
    sql_query: str
    question: str
    database_type: str
    success: bool

def build_prompt(question: str, db_type: str, schema: Optional[str] = None) -> str:
    parts = [SYSTEM_PROMPT, f"\nTarget database: {db_type}"]
    if schema:
        parts.append(f"\nDatabase Schema:\n{schema}")
    parts.append(f"\nQuestion: {question}\n\nSQL Query:")
    return "\n".join(parts)

def clean_sql_response(text: str) -> str:
    sql = text.strip()
    for fence in ["```sql", "```SQL", "```"]:
        if sql.startswith(fence):
            sql = sql[len(fence):]
    if sql.endswith("```"):
        sql = sql[:-3]
    return sql.strip()

# ── Gemini call with retry ────────────────────────────────────────────────────
def _call_gemini(prompt: str) -> str:
    """Blocking Gemini call — run in thread pool."""
    response = model.generate_content(prompt)
    return response.text

async def generate_with_retry(prompt: str, max_attempts: int = 3) -> str:
    """
    Throttled + retried Gemini call.
    1. Acquires a rate-limit slot (proactively avoids 429).
    2. On 429, waits 10s / 20s / 30s and retries.
    """
    last_error = None
    for attempt in range(max_attempts):
        # Proactive throttle — holds us under 10 RPM
        await _acquire_rate_limit_slot()
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, _call_gemini, prompt)
            return text
        except google_exceptions.ResourceExhausted as e:
            last_error = e
            wait_sec = 10 * (attempt + 1)   # 10s, 20s, 30s
            logger.warning(f"Rate limited (attempt {attempt+1}/{max_attempts}). Waiting {wait_sec}s…")
            await asyncio.sleep(wait_sec)
        except Exception as e:
            raise e
    raise last_error

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "active", "message": "AI SQL Generator", "version": "1.0.0"}

@app.get("/ping")
def ping():
    """Ultra-lightweight liveness probe — used by frontend for cold-start polling."""
    return {"ok": True}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "api_configured": bool(settings.gemini_api_key),
        "model": settings.model_name,
        "rate_limit_rpm": _RATE_LIMIT_RPM,
    }

@app.post("/generate_sql/", response_model=QueryResponse)
async def generate_sql(request: QueryRequest):
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question required")

        prompt = build_prompt(
            question=request.question.strip(),
            db_type=request.database_type,
            schema=request.schema
        )

        raw = await generate_with_retry(prompt)
        sql_query = clean_sql_response(raw)
        logger.info(f"Generated SQL for: {request.question[:60]}")

        return QueryResponse(
            sql_query=sql_query,
            question=request.question.strip(),
            database_type=request.database_type,
            success=True
        )
    except HTTPException:
        raise
    except google_exceptions.ResourceExhausted:
        raise HTTPException(
            status_code=429,
            detail=(
                "Gemini API rate limit reached after retries. "
                "You are on the free tier (15 RPM / 1,000 RPD). "
                "Please wait ~60 seconds and try again, or upgrade your API plan at aistudio.google.com."
            )
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Generation failed: {error_msg}")
        if "404" in error_msg:
            raise HTTPException(status_code=500, detail=f"Model '{settings.model_name}' not found. Check your API key.")
        if "API_KEY" in error_msg or "api key" in error_msg.lower():
            raise HTTPException(status_code=500, detail="Invalid or missing API key. Check GEMINI_API_KEY in Render settings.")
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
