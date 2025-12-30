"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging

from app.config import init_config
from app.db.database import init_db
from app.api.routes import router
from app.scheduler import start_scheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize config
# Support both /config/config.yaml (Docker) and ./config/config.yaml (local dev)
config_path = os.getenv("CONFIG_PATH", "/config/config.yaml")

# Try multiple paths
possible_paths = [
    config_path,
    "/config/config.yaml",
    "./config/config.yaml",
    os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml"),
]

config_path_found = None
for path in possible_paths:
    if os.path.exists(path):
        config_path_found = path
        break

if not config_path_found:
    error_msg = f"""
ERROR: Configuration file not found!

Tried the following paths:
{chr(10).join(f'  - {p}' for p in possible_paths)}

Please ensure:
1. The config directory is mounted in Docker: -v ./config:/config:ro
2. The file config/config.yaml exists (copy from config.example.yaml)
3. The CONFIG_PATH environment variable points to the correct file

Example setup:
  mkdir -p config
  cp config.example.yaml config/config.yaml
  # Edit config/config.yaml with your settings
"""
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)

logger.info(f"Loading configuration from: {config_path_found}")
init_config(config_path_found)

# Initialize database
data_dir = os.getenv("DATA_DIR", "/data")
try:
    init_db(data_dir)
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    logger.error(f"Data directory: {data_dir}")
    logger.error("Please ensure:")
    logger.error("1. The data volume is mounted: -v ./data:/data")
    logger.error("2. The directory has write permissions")
    logger.error("3. The DATA_DIR environment variable points to a writable path")
    raise

# Create FastAPI app
app = FastAPI(title="Media Janitor", version="1.0.0")

# Include API routes
app.include_router(router)

# Start scheduler
start_scheduler()

# Serve frontend static files
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dist / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend for all non-API routes."""
        if full_path.startswith("api/"):
            return None
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend not built"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Media Janitor API"}

