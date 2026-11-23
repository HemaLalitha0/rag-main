# =============================================================================
# AksharaMitra (అక్షరమిత్ర) – Production Dockerfile
# SHR Trinity Education Technology Innovation
# Runs internally on port 8501 (exposed on host localhost:8510 via Compose)
# =============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install minimal runtime OS utilities (curl for Docker healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application source (secrets & archives excluded via .dockerignore)
COPY . /app

# Create non-root user and ensure writable persistent directories
RUN useradd -m -u 1000 akshara && \
    mkdir -p /app/data /app/kb_cache /app/pdfs && \
    chown -R akshara:akshara /app

USER akshara

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "pages/AksharaMitra.py", "--server.port=8501", "--server.address=0.0.0.0"]
