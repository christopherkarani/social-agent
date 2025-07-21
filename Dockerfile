# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and entrypoint script
COPY src/ ./src/
COPY main.py .
COPY example_usage.py .
COPY docker-entrypoint.sh .

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Create directories for logs and configuration
RUN mkdir -p /app/logs /app/config

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default command
CMD ["python", "main.py", "scheduled"]