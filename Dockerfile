FROM texlive/texlive:latest AS runtime

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY src/. ./

RUN useradd --system --create-home appuser && chown -R appuser:appuser /app
ENV PATH="/opt/venv/bin:/usr/local/bin:/usr/bin:/bin"
USER appuser

EXPOSE 8000
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker latex_compile_service.main:app --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-2} --log-level info"]
