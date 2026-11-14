# Planet Explorer

A small full-stack app for exploring NASA imagery of the Moon and Mars. Pick a body, click a map tile or enter a coordinate, and get a real matching Earth geology tile from a supplied 10° dataset.

The app is intentionally simple: no database, no auth, no API keys, and no tile proxy. Map imagery is loaded directly from NASA.

## Features

- **Moon and Mars basemaps** from NASA Trek, on the same 2:1 equirectangular tile grid.
- **Two ways to choose a target**:
  - click a map tile for an area-weighted match; or
  - enter decimal-degree latitude/longitude for the 10° cell containing the point.
- **Real geology data** from the supplied `tiles_wide.csv`: Moon/Mars surface classes, mapped fraction, and age bins.
- **Earth analog matching** against Earth land tiles, with a confidence score, top three candidates, and an explicit “no reliable analog” state.
- **NASA GIBS preview** for each Earth candidate, with the matched 10° cell outlined.
- Zoom limits are enforced per body: Moon z0–8, Mars z0–7. Geology matching requires z2 or deeper.
- Responsive layout for desktop and mobile.

## Stack

| Layer    | Technology |
| -------- | ---------- |
| Frontend | React 19, TypeScript, Vite, Leaflet / react-leaflet, plain CSS |
| Backend  | Python 3.12+, FastAPI, Pydantic |
| Tooling  | `uv` (Python), `pnpm` (Node), pytest, Vitest |

## Quick start

### 1. Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

The API is available at <http://127.0.0.1:8000>, with interactive docs at <http://127.0.0.1:8000/docs>.

### 2. Frontend (development)

In a second terminal:

```bash
cd frontend
pnpm install
pnpm dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to the backend on port 8000.

### 3. Production-style build

Build the frontend, then start the backend. FastAPI serves the generated `frontend/dist` directory at the root URL.

```bash
cd frontend
pnpm build

cd ../backend
uv run uvicorn app.main:app --port 8000
```

Open <http://127.0.0.1:8000>.

## Using the app

1. Choose **Moon** or **Mars** in the header.
2. Either click a tile on the map, or type a latitude and longitude in the bar above the map and press **Go**.
   - Coordinates are decimal degrees.
   - Longitude is east-positive: `-180..180`.
   - Latitude is `-90..90`.
   - The map centers on the point at zoom 4 and shows the 10° geology cell.
3. The panel at the top shows the Earth match: confidence, shared-class mass, top similarity, Earth tile coverage, and the comparable compositions.
4. The tile section below shows the selected map tile and the raw Moon/Mars geology classes and age bins.

Clicking a map tile fills the coordinate bar with the clicked point. Pressing **Go** then refines the match to that single 10° cell.

## API

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/api/health` | Health check |
| GET | `/api/bodies` | Moon and Mars layer configuration |
| GET | `/api/tiles/{body}/{z}/{x}/{y}` | Tile metadata, bounds, approximate size, and aggregated geology |
| GET | `/api/matches/{body}/{z}/{x}/{y}` | Earth match for a map tile (z2 or deeper) |
| GET | `/api/matches/{body}/point?lat=...&lon=...` | Earth match for the 10° cell containing a coordinate |

Examples:

```bash
curl http://127.0.0.1:8000/api/tiles/moon/4/3/2
curl http://127.0.0.1:8000/api/matches/moon/4/3/2
curl "http://127.0.0.1:8000/api/matches/moon/point?lat=0&lon=0"
curl "http://127.0.0.1:8000/api/matches/mars/point?lat=-85&lon=-175"
```

Unknown bodies return `404`; invalid zoom levels, tile indexes, or coordinates return `422`. Tile matches below zoom 2 return `422` with a “too coarse” message.

## Matching method

The matcher is deliberately transparent and heuristic. It is a composition comparison, not a geologic provenance model.

### Data grid

The supplied table has 648 cells on an 18 × 36 grid. Each cell is 10° × 10°. Dataset rows run **south-to-north** (`r00` is the south pole), while NASA Trek map tile rows run north-to-south; the backend keeps those conventions separate.

A clicked map tile is matched by area-weighting every 10° cell that overlaps it. A coordinate is matched against its single containing 10° cell.

### Class crosswalk

Direct classes:

- volcanic → volcanic
- ice → ice
- Mars surficial_unconsolidated → Earth surficial_unconsolidated

Heuristic classes:

- Moon highlands → Earth plutonic + metamorphic (“crystalline”)
- Moon plains → Earth sedimentary

No Earth equivalent:

- impact
- Mars undivided_terrain

Unmatched classes are not forced onto an Earth class. They reduce the shared-area mass and therefore the confidence score.

### Earth candidates

Only Earth land tiles with at least 50% mapped coverage are considered. Ocean, blank, and no-data tiles are excluded. The Earth match vector is normalized over comparable classes, so water/no-data do not dominate the cosine similarity.

### Confidence

The confidence score combines:

- cosine similarity between the target and candidate comparable compositions;
- the share of the target area that has a comparable Earth class;
- the candidate’s mapped coverage;
- the similarity margin over the second candidate.

Scores map to high / medium / low / insufficient confidence. High or medium confidence produces a `match`; low confidence produces a `weak` match; everything else is `insufficient` and is labeled **No reliable analog**. The top three candidates are still returned for weak or insufficient matches when they exist, but they are clearly marked as reference-only.

## Data sources

- **Moon imagery**: [LRO WAC Global Mosaic](https://trek.nasa.gov/moon/) (`LRO_WAC_Mosaic_Global_303ppd_v02`) from NASA Trek.
- **Mars imagery**: [Viking Global Color Mosaic](https://trek.nasa.gov/mars/) (`Mars_Viking_MDIM21_ClrMosaic_global_232m`) from NASA Trek.
- **Earth preview**: [NASA GIBS Blue Marble Shaded Relief + Bathymetry](https://gibs.earthdata.nasa.gov/), requested as a WMS image around each candidate.
- **Geology table**: `backend/data/geology/tiles_wide.csv`, generated by the project owner for this app. The source rasters/vectors used to derive it are not included. See [`backend/data/geology/README.md`](backend/data/geology/README.md) for provenance, columns, and limitations.

Imagery is © NASA/JPL/USGS and is loaded directly in the browser from NASA servers. Attribution is displayed on the map.

## Known limitations

- **Earth coverage is land-only.** 238 of 648 cells have zero mapped area; 201 have at least 50% coverage and 156 have at least 80%. Ocean matches are impossible by design.
- **Taxonomy mismatch.** Earth has no impact, highlands, plains, or undivided-terrain classes in this table, and no Earth age data. Large parts of Mars are mapped as undivided terrain, so many Mars targets legitimately return “no reliable analog.”
- **Coarse cells.** 10° cells are much larger than NASA Trek imagery tiles. At the equator an Earth cell is about 13.4× the area of a Moon cell and 3.5× a Mars cell. A map tile can overlap several dataset cells.
- **Heuristic crosswalk.** Highlands → crystalline and plains → sedimentary are reasonable but simplified assumptions.
- **No Earth age comparison.** Age bins are shown for Moon/Mars context only.
- **Not a science product.** Similarity is a transparent composition heuristic, not a trained terrain or spectral embedding model.

## Tile grid notes

NASA Trek uses a 2:1 equirectangular grid, matching Leaflet's `L.CRS.EPSG4326`:

- `cols = 2^(z + 1)`, `rows = 2^z`
- Tile URL order is `{z}/{y}/{x}` (row before column)
- `west = -180 + (x / cols) * 360`, `north = 90 - (y / rows) * 180`

Trek does not expose a per-tile metadata endpoint, so bounds, center, and approximate size are computed by the backend from the tile index.

## Tests

```bash
# From the project root

# Backend
(cd backend && uv run pytest)

# Frontend unit tests
(cd frontend && pnpm test)

# Type-check + production build
(cd frontend && pnpm build)

# Lint
(cd frontend && pnpm lint)
```

## Project layout

```text
planet-explorer/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app and routes
│   │   ├── config.py        # Moon/Mars layer configuration
│   │   ├── tiles.py         # tile math and response building
│   │   ├── geology.py       # CSV loading, aggregation, matching
│   │   └── models.py        # Pydantic response models
│   ├── data/geology/        # supplied 10° table + data notes
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/      # map, coordinate bar, match card, panel
│   │   ├── lib/             # tile math, coordinates, geology helpers
│   │   └── api/client.ts
│   └── vite.config.ts       # /api dev proxy
└── README.md
```

## Possible next steps

- Replace the heuristic crosswalk with a trained terrain or spectral embedding model.
- Add more NASA layers (e.g., Mars MOLA/HRSC shaded relief, lunar mineralogy).
- Serve a dynamic WMTS capabilities document instead of hardcoded layer templates.
- Add shareable URLs for selected body/tile/point and Earth result.
- Add a small cache for precomputed tile geology summaries.

Not affiliated with NASA.
