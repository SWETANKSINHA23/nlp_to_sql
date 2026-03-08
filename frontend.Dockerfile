FROM python:3.11-slim as deps
WORKDIR /tmp
COPY frontend/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
FROM python:3.11-slim
RUN useradd -m -u 1000 app
WORKDIR /app
COPY --from=deps --chown=app:app /root/.local /home/app/.local
COPY --chown=app:app frontend/ .
USER app
ENV PATH=/home/app/.local/bin:$PATH
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]
