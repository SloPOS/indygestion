FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel && \
    pip install \
      fastapi==0.115.6 \
      uvicorn[standard]==0.34.0 \
      sqlalchemy==2.0.36 \
      alembic==1.14.1 \
      celery==5.4.0 \
      pydantic==2.10.4 \
      pydantic-settings==2.7.0 \
      psycopg[binary]==3.2.3 \
      asyncpg==0.30.0 \
      redis==5.2.1 \
      python-multipart==0.0.20 \
      httpx==0.28.1

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
