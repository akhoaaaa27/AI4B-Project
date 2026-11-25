from pathlib import Path

from fastapi.staticfiles import StaticFiles

from api.main import app

dist_dir = Path(__file__).resolve().parent / "web" / "dist"
app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")