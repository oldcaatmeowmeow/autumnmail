from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, paths
from .api.routes import router
from .store import db, repo

WEB_DIR = Path(__file__).parent / "web"


def create_app(token: str, dev: bool = False) -> FastAPI:
    paths.ensure_dirs()
    db.configure(paths.db_path())
    db.init()
    repo.initialize()

    app = FastAPI(
        title="秋信 AutumnMail",
        version=__version__,
        docs_url="/docs" if dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if dev else None,
    )
    app.state.token = token
    app.include_router(router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "version": __version__}

    index = WEB_DIR / "index.html"
    assets = WEB_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def index_page():
        if index.exists():
            return FileResponse(index)
        return JSONResponse(
            {"detail": "前端尚未构建，请先运行 npm run build。"}, status_code=503
        )

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if index.exists():
            return FileResponse(index)
        return JSONResponse(
            {"detail": "前端尚未构建，请先运行 npm run build。"}, status_code=503
        )

    return app
