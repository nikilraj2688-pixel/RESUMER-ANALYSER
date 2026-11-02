FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    HF_HUB_OFFLINE=0 \
    TRANSFORMERS_OFFLINE=0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy small model
RUN python -m spacy download en_core_web_sm

# Copy application source
COPY . .

EXPOSE 5000

CMD ["python", "run.py"]

