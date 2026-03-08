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

@st.cache_data(ttl=60)
def check_api_health() -> bool:
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
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
        timeout=90
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

# Initialize session state for rate limiting
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
        st.error("❌ API Unavailable")
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
            COOLDOWN_SECONDS = 15
            if time_since_last < COOLDOWN_SECONDS and st.session_state.request_count > 0:
                remaining = int(COOLDOWN_SECONDS - time_since_last)
                st.warning(f"⏳ Please wait {remaining} seconds before making another request to avoid rate limits.")
            else:
                with st.spinner("Generating..."):
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
                        st.success("✅ Generated successfully")
                    except requests.exceptions.Timeout:
                        st.warning("⏱️ Backend is cold-starting. Refresh and try again in 60 seconds.")
                    except requests.exceptions.ConnectionError:
                        st.error("🔌 Cannot reach backend. Service may be spinning up on Render.")
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 429:
                            st.error("⏳ Rate limit hit. Please wait 1 minute and retry.")
                        elif e.response.status_code == 503 or e.response.status_code == 0:
                            st.warning("🔄 Service is waking up (cold start). Please wait 30-60s and retry.")
                        else:
                            try:
                                detail = e.response.json().get("detail", e.response.text)
                            except Exception:
                                detail = e.response.text
                            st.error(f"❌ Backend error {e.response.status_code}: {detail}")
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
