import streamlit as st
import requests
from typing import Optional
import time
import os
import base64

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

# ── Health / wake helpers ────────────────────────────────────────────────────

def check_api_health() -> bool:
    """Single lightweight health probe — NOT cached so it always reflects reality."""
    try:
        response = requests.get(f"{API_URL}/ping", timeout=4)
        return response.status_code == 200
    except Exception:
        return False

def wake_backend() -> bool:
    """
    Proactively ping the backend until it wakes up.
    6 attempts × 5 s = max 30 s (Render free tier typically wakes in 10-20 s).
    """
    MAX_ATTEMPTS = 6
    POLL_INTERVAL = 5   # seconds between probes

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.get(f"{API_URL}/ping", timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)
    return False

# ── Proactive background wake on first page load ─────────────────────────────
# Fires once per browser session so that by the time the user clicks Generate
# the cold-start delay is already absorbed.
if "backend_ready" not in st.session_state:
    st.session_state.backend_ready = check_api_health()

if not st.session_state.backend_ready:
    # Show a one-time warming banner at the top of the page
    with st.status("🔄 Backend warming up… (this takes ~10–20 s on first visit)", expanded=False) as status_box:
        st.session_state.backend_ready = wake_backend()
        if st.session_state.backend_ready:
            status_box.update(label="✅ Backend is ready!", state="complete", expanded=False)
        else:
            status_box.update(label="⚠️ Backend slow to respond — will retry on Generate", state="error", expanded=False)

# ── SQL generation ────────────────────────────────────────────────────────────

def generate_query(question: str, schema: Optional[str], db_type: str) -> dict:
    payload = {
        "question": question.strip(),
        "schema": schema.strip() if schema else None,
        "database_type": db_type
    }
    response = requests.post(
        f"{API_URL}/generate_sql/",
        json=payload,
        timeout=60   # generous but not 2 min — backend is already awake by now
    )
    response.raise_for_status()
    return response.json()

# ── Image helper ──────────────────────────────────────────────────────────────

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

# ── Header ────────────────────────────────────────────────────────────────────

icon_base64 = get_base64_image("sql.png")
st.markdown(
    f'<h1 class="main-header"><img src="data:image/png;base64,{icon_base64}" '
    f'width="60" style="vertical-align: bottom;"> SQL Query Generator</h1>',
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align: center; color: #666;'><b>Natural language to SQL using AI</b></div>",
    unsafe_allow_html=True
)

# ── Session state ─────────────────────────────────────────────────────────────

if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0
if "request_count" not in st.session_state:
    st.session_state.request_count = 0

# ── Sidebar ───────────────────────────────────────────────────────────────────

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
    # Live (uncached) status check
    if st.session_state.backend_ready or check_api_health():
        st.session_state.backend_ready = True
        st.success("✅ API Connected")
    else:
        st.warning("🔄 API warming up…")
    st.divider()
    st.caption(f"Requests: {st.session_state.request_count}")

# ── Main content ──────────────────────────────────────────────────────────────

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
                st.warning(f"⏳ Please wait {remaining} seconds…")
            else:
                # Ensure backend is awake before generating
                if not st.session_state.backend_ready and not check_api_health():
                    with st.spinner("🔄 Backend is starting up, please wait (up to 30s)…"):
                        if not wake_backend():
                            st.error("❌ Backend is unavailable. Please wait a moment and try again.")
                            st.stop()
                        st.session_state.backend_ready = True

                # Generate SQL
                with st.spinner("🤖 Generating SQL…"):
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
                        st.session_state.backend_ready = False
                        st.error("⏱️ Request timed out. The backend may be overloaded. Try again in 15 seconds.")
                    except requests.exceptions.ConnectionError:
                        st.session_state.backend_ready = False
                        st.error("🔌 Cannot reach backend. Service may be restarting — refresh the page.")
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 429:
                            st.error(
                                "⏳ **API Rate Limit Hit.**\n\n"
                                "The free Gemini API quota is exhausted. "
                                "Please wait ~1 minute or generate a new API key at "
                                "[aistudio.google.com](https://aistudio.google.com) "
                                "and update it in Render settings."
                            )
                        elif e.response.status_code in (503, 502):
                            st.session_state.backend_ready = False
                            st.warning("🔄 Backend restarting. Please wait 15s and retry.")
                        else:
                            try:
                                detail = e.response.json().get("detail", e.response.text)
                            except Exception:
                                detail = e.response.text
                            st.error(f"❌ Error {e.response.status_code}: {detail}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")

# ── Footer ────────────────────────────────────────────────────────────────────

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
