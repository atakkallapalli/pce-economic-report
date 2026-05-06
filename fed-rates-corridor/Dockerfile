# =============================================================================
# Multi-stage Dockerfile for Fed Rates Corridor Streamlit App
# =============================================================================

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    pip install --no-cache-dir --prefix=/install boto3>=1.34

# Stage 2: Production image
FROM python:3.11-slim AS production

# Security: run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . /app/

# Download initial data (will be refreshed by scheduled task in production)
RUN python download_rates.py || true

# Security: remove unnecessary files and set permissions
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run Streamlit with security settings
ENTRYPOINT ["streamlit", "run", "app/streamlit_app.py", \
    "--server.port=8501", \
    "--server.headless=true", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=true", \
    "--browser.gatherUsageStats=false", \
    "--server.fileWatcherType=none"]
