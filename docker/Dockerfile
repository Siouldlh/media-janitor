# Build stage for frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json ./
# npm ci requires package-lock.json, npm install works without it
RUN npm install --frozen-lockfile || npm install

COPY frontend/ .
RUN npm run build

# Python stage
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify critical dependencies are installed
RUN python -c "import qbittorrentapi; print('✓ qbittorrentapi imported successfully')" && \
    python -c "import plexapi; print('✓ plexapi imported successfully')" && \
    python -c "import fastapi; print('✓ fastapi imported successfully')" || \
    (echo "ERROR: Critical dependencies not installed correctly" && exit 1)

# Copy application code
COPY app/ ./app/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8099

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]

