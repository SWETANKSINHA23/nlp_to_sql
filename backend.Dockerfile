FROM python:3.11-slim as deps
WORKDIR /tmp
COPY backend/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
FROM python:3.11-slim
RUN useradd -m -u 1000 app
WORKDIR /app
COPY --from=deps --chown=app:app /root/.local /home/app/.local
COPY --chown=app:app backend/ .
USER app
ENV PATH=/home/app/.local/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
