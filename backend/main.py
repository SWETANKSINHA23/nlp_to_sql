from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai
from typing import Optional
import logging
import asyncio
from config import settings
from google.api_core import exceptions as google_exceptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app = FastAPI(title="SQL Query Generator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def _call_gemini(prompt: str) -> str:
    """Blocking Gemini call — run in thread pool."""
    response = model.generate_content(prompt)
    return response.text

async def generate_with_retry(prompt: str, max_attempts: int = 3) -> str:
    """Async retry wrapper — handles 429 properly across thread boundaries."""
    last_error = None
    for attempt in range(max_attempts):
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, _call_gemini, prompt)
            return text
        except google_exceptions.ResourceExhausted as e:
            last_error = e
            wait_sec = 5 * (attempt + 1)    # 5s, 10s, 15s  (fast retry)
            logger.warning(f"Rate limited (attempt {attempt+1}). Waiting {wait_sec}s…")
            await asyncio.sleep(wait_sec)
        except Exception as e:
            raise e
    raise last_error

@app.get("/")
def root():
    return {"status": "active", "message": "AI SQL Generator", "version": "1.0.0"}

@app.get("/ping")
def ping():
    """Ultra-lightweight liveness probe — used by frontend for cold-start polling."""
    return {"ok": True}

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
        raise HTTPException(status_code=429, detail="API rate limit exceeded. Please wait a minute and retry.")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Generation failed: {error_msg}")
        if "404" in error_msg:
            raise HTTPException(status_code=500, detail=f"Model '{settings.model_name}' not found. Check API key & model name.")
        if "API_KEY" in error_msg or "api key" in error_msg.lower():
            raise HTTPException(status_code=500, detail="Invalid or missing API key. Check GEMINI_API_KEY environment variable.")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "api_configured": bool(settings.gemini_api_key),
        "model": settings.model_name
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
