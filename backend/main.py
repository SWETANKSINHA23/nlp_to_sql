from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai
from typing import Optional
import logging
from config import settings
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
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
- Generate SQL only, no explanations
- Use standard syntax compatible with PostgreSQL, MySQL, BigQuery, Redshift, Snowflake
- Include proper WHERE, JOIN, GROUP BY clauses as needed
- Use appropriate aggregations (SUM, AVG, COUNT)
- Format with proper indentation
- Return query without markdown blocks"""

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    schema: Optional[str] = Field(default=None)
    database_type: str = Field(default="PostgreSQL")

class QueryResponse(BaseModel):
    sql_query: str
    question: str
    database_type: str
    success: bool

def build_prompt(question: str, schema: Optional[str] = None) -> str:
    if schema:
        return f"Database Schema:\n{schema}\n\nQuestion: {question}\n\nGenerate SQL query:"
    return f"Convert to SQL: {question}"

def clean_sql_response(response: str) -> str:
    sql = response.strip()
    if sql.startswith("```sql"):
        sql = sql.replace("```sql", "").replace("```", "").strip()
    elif sql.startswith("```"):
        sql = sql.replace("```", "").strip()
    return sql

@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(google_exceptions.ResourceExhausted),
    reraise=True
)
def generate_content_with_retry(chat, prompt):
    return chat.send_message(prompt)

@app.get("/")
def root():
    return {"status": "active", "version": "1.0.0"}

@app.post("/generate_sql/", response_model=QueryResponse)
async def generate_sql(request: QueryRequest):
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question required")
        question = request.question.strip()
        prompt = build_prompt(question, request.schema)
        chat = model.start_chat(history=[])
        
        # retry-wrapped function
        response = generate_content_with_retry(chat, f"{SYSTEM_PROMPT}\n\n{prompt}")
        sql_query = clean_sql_response(response.text)
        logger.info(f"Generated SQL for: {question[:50]}")
        return QueryResponse(
            sql_query=sql_query,
            question=question,
            database_type=request.database_type,
            success=True
        )        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Generation failed: {error_msg}")
        if "429" in error_msg or isinstance(e, google_exceptions.ResourceExhausted):
            raise HTTPException(status_code=429, detail="API Quota Exceeded. Please try again later.")
        if "404" in error_msg:
             raise HTTPException(status_code=404, detail=f"Model {settings.model_name} not found.")
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
