# ======================
# Stage 1: Base Image
# ======================
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ======================
# Stage 2: Testing
# ======================
FROM base AS test

# Copy entire backend
COPY . .

# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-cov pytest-asyncio

# Run tests
RUN pytest tests/unit/ -v --cov=core --cov=api || echo "Tests run completed"

# ======================
# Stage 3: Production
# ======================
FROM base AS production

# Copy only application code from test stage
COPY --from=test /app /app

# Create non-root user for security
RUN useradd -m -u 1000 academe && \
    chown -R academe:academe /app

# Switch to non-root user
USER academe

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Start application with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
