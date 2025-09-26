# Multi-stage Dockerfile for FundLink components

# Base stage with common dependencies
FROM python:3.11-slim-bullseye as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

# Web service (Django backend)
FROM base as web

# Copy web requirements and install
COPY fundlink_web/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install gunicorn for production
RUN pip install gunicorn

# Copy web application
COPY fundlink_web/ .

# Expose port
EXPOSE 8000

# Production command - can be overridden in docker-compose
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "fundlink_backend.wsgi:application"]

# Bot service (Telegram bot)
FROM base as bot

# Copy bot requirements and install
COPY telbot_llm/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy bot application
COPY telbot_llm/ .

# Command to run bot
CMD ["python", "run_bot.py"]

# Verifier service (Donation verifier)
FROM base as verifier

# Copy verifier requirements and install
COPY donation_verifier/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy verifier application
COPY donation_verifier/ ./donation_verifier/

# Create an __init__.py to make it a package and a launcher script
RUN touch donation_verifier/__init__.py
RUN echo "from donation_verifier.main import main; main()" > run_verifier.py

# Command to run verifier
CMD ["python", "run_verifier.py"]
