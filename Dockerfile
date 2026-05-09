FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements-demo.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements-demo.txt

# Copy project files
COPY . .

# Expose ports for both Flask (5000) and Streamlit (8502)
EXPOSE 5000 8502

# The default command runs the API, but docker-compose will override this for the dashboard
CMD ["python", "-m", "src.api.app"]
