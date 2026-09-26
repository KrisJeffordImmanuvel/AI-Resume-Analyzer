# Truescope as one web service: the backend serves the built web page and the API.
# Used by Render (render.yaml); see README, "Publish on Render".

# ---- 1. Build the web page ----
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2. The server ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app/backend

# Everything in requirements.txt except the optional semantic matching (it pulls in PyTorch,
# several GB) and the test runner. The app works without them (SEMANTIC_MATCHING is off).
COPY backend/requirements.txt ./requirements.txt
RUN grep -v -E "^(sentence-transformers|pytest)==" requirements.txt > requirements-server.txt \
    && pip install -r requirements-server.txt

COPY backend/ ./
COPY samples/ /app/samples/
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# The database lives on the service's disk (render.yaml mounts it at /var/data).
ENV FRONTEND_DIST=/app/frontend/dist \
    DATABASE_URL=sqlite:////var/data/app.db \
    SEMANTIC_MATCHING=false
RUN mkdir -p /var/data

EXPOSE 8000
# Render sets PORT. --proxy-headers: trust Render's proxy for https and the visitor's address.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
