# Build stage for frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json ./
# npm ci requires package-lock.json, npm install works without it
RUN npm install --frozen-lockfile || npm install

COPY frontend/ .
RUN npm run build

# Python stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r mediajanitor && useradd -r -g mediajanitor mediajanitor

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify critical dependencies are installed
RUN python -c "import qbittorrentapi; print('✓ qbittorrentapi imported successfully')" && \
    python -c "import fastapi; print('✓ fastapi imported successfully')" && \
    python -c "import structlog; print('✓ structlog imported successfully')" && \
    python -c "import tenacity; print('✓ tenacity imported successfully')" || \
    (echo "ERROR: Critical dependencies not installed correctly" && exit 1)

# Copy application code
COPY app/ ./app/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory with proper permissions for non-root user
RUN mkdir -p /data && chown -R mediajanitor:mediajanitor /data

# Switch to non-root user
USER mediajanitor

# Expose port
EXPOSE 8099

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8099/')" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]

