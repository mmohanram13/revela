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
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# Expose port (Cloud Run routes HTTPS/443 to this port internally)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "application/app.py", "--server.port=8080", "--server.address=0.0.0.0"]
