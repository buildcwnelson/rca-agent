# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install git (required by GitPython for forensics) and certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Fix Git dubious ownership issue when host volumes are mounted with different UID/GID
RUN git config --global --add safe.directory "*"

# Set working directory for application code
WORKDIR /app

# Copy dependency definition files first for optimal Docker layer caching
COPY pyproject.toml README.md ./

# Install application and production dependencies
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Create default directories for mounting repositories and storing output reports
RUN mkdir -p /repo /output && chmod 777 /repo /output

# Working directory when running container
WORKDIR /repo

# Set entrypoint to rca-agent CLI
ENTRYPOINT ["rca-agent"]
CMD ["investigate", "--help"]
