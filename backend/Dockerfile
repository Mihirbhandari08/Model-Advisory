# ─── Stage 1: Builder ───────────────────────────────────────────────────────
FROM python:3.9-slim AS builder

WORKDIR /app

# Install build dependencies only in this stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install into a local prefix so we can copy cleanly
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Runtime ───────────────────────────────────────────────────────
FROM python:3.9-slim AS runtime

# Security: run as non-root user
RUN useradd --create-home appuser

WORKDIR /app

# Pull only the installed packages from builder — no gcc, no cache
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]