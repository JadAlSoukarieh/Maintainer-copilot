from __future__ import annotations

from fastapi import FastAPI

from maintcopilot_model_server.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Maintainer's Copilot Model Server", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()
