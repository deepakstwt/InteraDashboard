# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    git \
    chromium-driver \
    chromium \
    libnss3 \
    libgconf-2-4 \
    libxi6 \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . .

# Streamlit specific config (can override) 
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    USE_LIVE_VAHAN=0

EXPOSE 8501

# Default command runs dashboard
CMD ["streamlit", "run", "src/dashboard/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
