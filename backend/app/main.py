from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import BODIES
from .earth import random_earth_tile
from .models import BodiesResponse, EarthAnalogResponse, TileResponse
from .tiles import build_tile_response

app = FastAPI(
    title="Planet Explorer API",
    version="0.1.0",
    description=(
        "Tile metadata for the NASA Trek Moon and Mars WMTS layers, "
        "plus a placeholder Earth analog picker."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/bodies", response_model=BodiesResponse)
def list_bodies() -> BodiesResponse:
    return BodiesResponse(bodies=list(BODIES.values()))


@app.get("/api/tiles/{body}/{z}/{x}/{y}", response_model=TileResponse)
def get_tile(body: str, z: int, x: int, y: int) -> TileResponse:
    config = BODIES.get(body)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown body '{body}'. Expected one of: {', '.join(BODIES)}.",
        )

    try:
        return build_tile_response(config, z, x, y)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/earth/random", response_model=EarthAnalogResponse)
def get_earth_random(
    seed: int | None = Query(
        default=None,
        ge=0,
        le=2**31 - 1,
        description="Optional seed for a reproducible random tile.",
    ),
) -> EarthAnalogResponse:
    return random_earth_tile(seed)


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIST), html=True),
        name="frontend",
    )
else:

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "name": app.title,
            "docs": "/docs",
            "frontend": "Not built yet. Run `pnpm build` in frontend/ to serve the UI from here.",
        }
