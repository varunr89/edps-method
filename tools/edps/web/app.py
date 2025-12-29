"""FastAPI application for EDPS web UI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="EDPS Method", docs_url=None, redoc_url=None)

# Static files will be mounted after templates are set up
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
