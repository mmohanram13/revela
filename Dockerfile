# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml ./
COPY application/ ./application/

# Install Python dependencies using uv
RUN uv pip install --system --no-cache .

# Set environment variables for Cloud Run
ENV ENVIRONMENT=production
ENV SERVER_PORT=8080
ENV SERVER_ADDRESS=0.0.0.0

# Expose port (Cloud Run routes HTTPS/443 to this port internally)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the Flask app using gunicorn for production
RUN uv pip install --system --no-cache gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "application.app:app"]
