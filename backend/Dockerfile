FROM python:3.13-slim
<<<<<<< HEAD
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
WORKDIR /app/backend
EXPOSE 8000
=======

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Run as an unprivileged user. /data holds the SQLite database volume.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin sentinel \
    && mkdir -p /data \
    && chown sentinel:sentinel /data
COPY --chown=sentinel:sentinel backend /app/backend

WORKDIR /app/backend
USER sentinel
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=2)"
>>>>>>> 4f3f30c (feat:Phase 6 -Testing, Security and DevOps)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
