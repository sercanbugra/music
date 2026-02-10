# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=/app/pretrained_models

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Preload all stem models at build-time to avoid runtime model downloads.
RUN mkdir -p /app/pretrained_models/2stems \
    && curl -L "https://github.com/deezer/spleeter/releases/download/v1.4.0/2stems.tar.gz" -o /tmp/2stems.tar.gz \
    && tar -xzf /tmp/2stems.tar.gz -C /app/pretrained_models/2stems \
    && echo OK > /app/pretrained_models/2stems/.probe \
    && rm -f /tmp/2stems.tar.gz \
    && mkdir -p /app/pretrained_models/4stems \
    && curl -L "https://github.com/deezer/spleeter/releases/download/v1.4.0/4stems.tar.gz" -o /tmp/4stems.tar.gz \
    && tar -xzf /tmp/4stems.tar.gz -C /app/pretrained_models/4stems \
    && echo OK > /app/pretrained_models/4stems/.probe \
    && rm -f /tmp/4stems.tar.gz \
    && mkdir -p /app/pretrained_models/5stems \
    && curl -L "https://github.com/deezer/spleeter/releases/download/v1.4.0/5stems.tar.gz" -o /tmp/5stems.tar.gz \
    && tar -xzf /tmp/5stems.tar.gz -C /app/pretrained_models/5stems \
    && echo OK > /app/pretrained_models/5stems/.probe \
    && rm -f /tmp/5stems.tar.gz

COPY . .

EXPOSE 8080
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "1", "--timeout", "300"]

