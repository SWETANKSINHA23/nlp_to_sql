import streamlit as st
import requests
from typing import Optional
import time
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="SQL Query Generator",
    page_icon="sql.png",
    layout="wide"
)
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)
def check_api_health() -> bool:
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def wake_backend() -> bool:
    """Ping the backend repeatedly until it wakes up (handles cold starts)."""
    for attempt in range(8):  # try for up to ~80 seconds
        try:
            response = requests.get(f"{API_URL}/health", timeout=10)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(10)
    return False

def generate_query(question: str, schema: Optional[str], db_type: str) -> dict:
    payload = {
        "question": question.strip(),
        "schema": schema.strip() if schema else None,
        "database_type": db_type
    }
    response = requests.post(
        f"{API_URL}/generate_sql/",
        json=payload,
        timeout=120  # increased to 2 minutes to cover cold start + generation
    )
    response.raise_for_status()
    return response.json()

import base64

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

icon_base64 = get_base64_image("sql.png")
st.markdown(f'<h1 class="main-header"><img src="data:image/png;base64,{icon_base64}" width="60" style="vertical-align: bottom;"> SQL Query Generator</h1>', unsafe_allow_html=True)
st.markdown("<div style='text-align: center; color: #666;'><b>Natural language to SQL using AI</b></div>", unsafe_allow_html=True)

# Initialize session state
if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

with st.sidebar:
    st.header("⚙️ Configuration")
    db_type = st.selectbox(
        "Target Database",
        ["PostgreSQL", "MySQL", "BigQuery", "Redshift", "Snowflake", "SQLite"]
    )
    st.divider()
    st.subheader("📊 Schema (Optional)")
    schema = st.text_area(
        "Paste database schema:",
        placeholder="Table: sales_data\nColumns: id, region, sales, date",
        height=200
    )
    st.divider()
    if check_api_health():
        st.success("✅ API Connected")
    else:
        st.warning("⏳ API waking up...")
    st.divider()
    st.caption(f"Requests: {st.session_state.request_count}")

col1, col2 = st.columns(2)
with col1:
    st.subheader("💬 Enter Question")
    examples = [
        "Show total sales by region in 2024",
        "Find top 10 customers by revenue",
        "Average order value per month",
        "Products with sales > $10,000",
        "Year-over-year growth by category"
    ]
    selected = st.selectbox("Examples:", [""] + examples)
    question = st.text_area(
        "Your question:",
        value=selected if selected else "",
        placeholder="e.g., Show total sales by region",
        height=150
    )
    generate = st.button("🚀 Generate SQL", type="primary", use_container_width=True)

with col2:
    st.subheader("📝 Generated Query")
    if generate:
        if not question.strip():
            st.warning("⚠️ Enter a question")
        else:
            time_since_last = time.time() - st.session_state.last_request_time
            COOLDOWN_SECONDS = 5
            if time_since_last < COOLDOWN_SECONDS and st.session_state.request_count > 0:
                remaining = int(COOLDOWN_SECONDS - time_since_last)
                st.warning(f"⏳ Please wait {remaining} seconds...")
            else:
                # Step 1: Wake backend if needed
                if not check_api_health():
                    with st.spinner("🔄 Backend is starting up, please wait (up to 60s)..."):
                        if not wake_backend():
                            st.error("❌ Backend is unavailable. Please wait a minute and try again.")
                            st.stop()

                # Step 2: Generate SQL
                with st.spinner("🤖 Generating SQL..."):
                    try:
                        st.session_state.last_request_time = time.time()
                        st.session_state.request_count += 1
                        result = generate_query(question, schema, db_type)
                        sql = result["sql_query"]
                        st.code(sql, language="sql")
                        st.download_button(
                            "📋 Download SQL",
                            sql,
                            "query.sql",
                            "text/plain"
                        )
                        st.success("✅ Generated successfully!")
                    except requests.exceptions.Timeout:
                        st.error("⏱️ Request timed out. The backend may be overloaded. Try again in 30 seconds.")
                    except requests.exceptions.ConnectionError:
                        st.error("🔌 Cannot reach backend. Service may be restarting.")
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 429:
                            st.error("⏳ **API Rate Limit Hit.**\n\nThe free Gemini API quota is exhausted. Please wait ~1 hour or generate a new API key at [aistudio.google.com](https://aistudio.google.com) and update it in Render settings.")
                        elif e.response.status_code in (503, 502):
                            st.warning("🔄 Backend starting up. Please wait 30s and retry.")
                        else:
                            try:
                                detail = e.response.json().get("detail", e.response.text)
                            except Exception:
                                detail = e.response.text
                            st.error(f"❌ Error {e.response.status_code}: {detail}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")

st.divider()
feat1, feat2, feat3 = st.columns(3)
with feat1:
    st.info("**🎯 AI-Powered**\nGoogle Gemini integration")
with feat2:
    st.info("**🗄️ Multi-Database**\n6 database types supported")
with feat3:
    st.info("**📊 Schema-Aware**\nOptional context for accuracy")
st.divider()
st.caption("Built with FastAPI, Streamlit & Google Gemini | 2026")
