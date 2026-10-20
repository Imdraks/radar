FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user BEFORE installing Playwright
RUN adduser --disabled-password --gecos '' appuser

# Copy requirements first for caching
COPY requirements.txt .
RUN python -m pip install --no-cache-dir pip==26.2.1 && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers as appuser (important for cache location)
USER appuser
RUN playwright install chromium
USER root

# Copy application code
COPY . .

# Set ownership and switch to appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
