from __future__ import annotations

import hashlib
import random

from .models import AnalysisField, BodyId, TileAnalysis

MOON_TERRAINS = (
    "Cratered highlands",
    "Smooth maria",
    "Rugged basin rim",
    "Volcanic plains",
    "Regolith-covered plateau",
)

MOON_POLAR_TERRAINS = (
    "Polar highlands",
    "Permanently shadowed terrain",
    "Ice-bearing polar basin",
)

MARS_TERRAINS = (
    "Cratered highlands",
    "Aeolian plains",
    "Dune fields",
    "Volcanic plateau",
    "Canyon terrain",
    "Outflow channel",
)

MARS_POLAR_TERRAINS = (
    "Polar layered deposits",
    "Ice-rich polar terrain",
    "Frozen dune field",
)


def _rng(body: BodyId, z: int, x: int, y: int) -> random.Random:
    """Stable RNG: the same tile always produces the same placeholder values."""
    digest = hashlib.sha256(f"{body}:{z}:{x}:{y}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def build_analysis(
    body: BodyId, z: int, x: int, y: int, center_lat: float
) -> TileAnalysis:
    rng = _rng(body, z, x, y)
    polar = abs(center_lat) > 72.0

    if body == "moon":
        terrain = rng.choice(MOON_POLAR_TERRAINS if polar else MOON_TERRAINS)
        elevation = rng.randint(-8400, 10300)
        slope = round(rng.uniform(0.3, 20.0), 1)
        crater_density = round(rng.uniform(0.2, 3.6), 2)
        albedo = round(rng.uniform(7.5, 25.0), 1)
        confidence = rng.randint(72, 97)

        fields = [
            AnalysisField(label="Terrain class", value=terrain),
            AnalysisField(label="Elevation", value=f"{elevation:,}", unit="m"),
            AnalysisField(label="Mean slope", value=f"{slope:.1f}", unit="°"),
            AnalysisField(
                label="Crater density", value=f"{crater_density:.2f}", unit="per km²"
            ),
            AnalysisField(label="Normal albedo", value=f"{albedo:.1f}", unit="%"),
        ]
    else:
        terrain = rng.choice(MARS_POLAR_TERRAINS if polar else MARS_TERRAINS)
        elevation = rng.randint(-8200, 21200)
        slope = round(rng.uniform(0.4, 22.0), 1)
        dust_cover = rng.randint(4, 92)
        thermal_inertia = rng.randint(80, 600)
        rock_abundance = rng.randint(2, 28)
        confidence = rng.randint(68, 96)

        fields = [
            AnalysisField(label="Terrain class", value=terrain),
            AnalysisField(label="Elevation", value=f"{elevation:,}", unit="m"),
            AnalysisField(label="Mean slope", value=f"{slope:.1f}", unit="°"),
            AnalysisField(label="Dust cover", value=f"{dust_cover}", unit="%"),
            AnalysisField(
                label="Thermal inertia", value=f"{thermal_inertia}", unit="TIU"
            ),
            AnalysisField(label="Rock abundance", value=f"{rock_abundance}", unit="%"),
        ]

    return TileAnalysis(
        summary=f"{terrain} · placeholder profile derived from tile coordinates.",
        confidence_pct=confidence,
        fields=fields,
    )
