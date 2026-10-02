FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

WORKDIR /app

# System deps (build tools for any wheels + dnspython is pure python so ok)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# HF Spaces default port
EXPOSE 7860

# gthread worker is required for SSE streaming — sync worker would block
CMD ["gunicorn", \
     "-b", "0.0.0.0:7860", \
     "-w", "1", \
     "--threads", "8", \
     "-k", "gthread", \
     "--timeout", "0", \
     "--keep-alive", "65", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]