from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1 import api_router
from app.core.config import settings

app = FastAPI(title="Qatra API", version=settings.engine_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Qatra", "docs": "/docs", "health": "/api/v1/health"}
