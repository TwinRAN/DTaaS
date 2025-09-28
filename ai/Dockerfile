FROM python:3.11-slim

# --- Runtime defaults & cleanliness ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    DEFAULT_MODEL_NAME=RandomForestRegressor_win07

WORKDIR /app

# --- Install deps first for better caching ---
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# --- Copy app code & model files ---
COPY app/ app/
COPY ml-models/ ml-models/
COPY wsgi.py run_dev.py ./
COPY .env ./

# --- Non-root user for security ---
RUN useradd -m appuser
USER appuser

# NOTE: EXPOSE is informational; keep default. Use -p / compose to publish.
EXPOSE 8000

# --- Healthcheck: hits /health on current PORT (env) ---
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python","-c","import http.client,sys,os; p=int(os.getenv('PORT','8000')); c=http.client.HTTPConnection('127.0.0.1',p,timeout=2); c.request('GET','/health'); sys.exit(0 if c.getresponse().status==200 else 1)"]

# --- Run server; PORT & HOST resolved at *runtime* ---
# Using sh -c ensures env var expansion when the container starts.
CMD ["sh","-c","waitress-serve --host=${HOST:-0.0.0.0} --port=${PORT:-8000} wsgi:app"]
