from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import BODIES
from .geology import MATCH_MIN_ZOOM, build_point_match, build_tile_match
from .models import BodiesResponse, BodyInfo, MatchResponse, TileResponse
from .tiles import build_tile_response, tile_bounds, validate_tile

app = FastAPI(
    title="Planet Explorer API",
    version="0.2.0",
    description=(
        "Tile metadata and geology-based Earth analogs for the NASA Trek "
        "Moon and Mars WMTS layers."
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


def get_body(body: str) -> BodyInfo:
    config = BODIES.get(body)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown body '{body}'. Expected one of: {', '.join(BODIES)}.",
        )
    return config


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/bodies", response_model=BodiesResponse)
def list_bodies() -> BodiesResponse:
    return BodiesResponse(bodies=list(BODIES.values()))


@app.get("/api/tiles/{body}/{z}/{x}/{y}", response_model=TileResponse)
def get_tile(body: str, z: int, x: int, y: int) -> TileResponse:
    config = get_body(body)
    try:
        return build_tile_response(config, z, x, y)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/matches/{body}/point", response_model=MatchResponse)
def get_point_match(
    body: str,
    lat: float = Query(
        ...,
        ge=-90,
        le=90,
        description="Latitude in decimal degrees.",
    ),
    lon: float = Query(
        ...,
        ge=-180,
        le=180,
        description="Longitude in decimal degrees, east-positive.",
    ),
) -> MatchResponse:
    config = get_body(body)
    try:
        return build_point_match(config, lat, lon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/matches/{body}/{z}/{x}/{y}", response_model=MatchResponse)
def get_tile_match(body: str, z: int, x: int, y: int) -> MatchResponse:
    config = get_body(body)
    try:
        validate_tile(z, x, y, min_zoom=config.min_zoom, max_zoom=config.max_zoom)
        if z < MATCH_MIN_ZOOM:
            raise ValueError(
                f"Zoom {z} is too coarse for geology matching; "
                f"zoom to level {MATCH_MIN_ZOOM} or deeper."
            )
        bounds = tile_bounds(z, x, y)
        return build_tile_match(config, z, x, y, bounds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
