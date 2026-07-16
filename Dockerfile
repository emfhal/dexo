# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install system dependencies needed for native extensions and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Enable bytecode compilation and use standard locations
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
# Do not use virtualenvs inside the Docker container
ENV UV_SYSTEM_PYTHON=1

# Install dependencies first for better caching
# Copying only pyproject.toml and uv.lock (if it exists) initially
COPY pyproject.toml .
# We use `uv pip install` with system python or `uv sync`
RUN uv pip install -e . --system

# Install playwright browsers
RUN playwright install chromium --with-deps

# Copy the rest of the application
COPY src/ ./src/

# Expose the API port
EXPOSE 8080

# Environment setup
ENV HOST=0.0.0.0
ENV PORT=8080
ENV ENVIRONMENT=production

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
