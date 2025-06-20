# Multi-stage Docker build for EDI X12 278 Processor
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements_deploy.txt .
RUN pip install --no-cache-dir --user -r requirements_deploy.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY . .

# Set ownership
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Make sure scripts in .local are usable
ENV PATH=/home/app/.local/bin:$PATH

# Create required directories
RUN mkdir -p uploads outputs temp logs

# Set environment variables
ENV PYTHONPATH=/app
ENV STREAMLIT_CONFIG_FILE=/app/.streamlit/config.toml
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Expose port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "streamlit_deploy.py", "--server.port=8501", "--server.address=0.0.0.0"] 