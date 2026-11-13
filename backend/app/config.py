from .models import BodyInfo, LayerInfo

MOON_LAYER = LayerInfo(
    label="LRO_WAC_Mosaic_Global_303ppd_v02",
    title="LRO WAC Global Mosaic",
    instrument="Lunar Reconnaissance Orbiter · Wide Angle Camera",
    resolution="303 ppd (~120 m/px)",
)

MARS_LAYER = LayerInfo(
    label="Mars_Viking_MDIM21_ClrMosaic_global_232m",
    title="Viking Global Color Mosaic",
    instrument="Viking 1 & 2 · Visual Imaging Subsystem",
    resolution="232 m/px",
)

BODIES: dict[str, BodyInfo] = {
    "moon": BodyInfo(
        id="moon",
        name="Moon",
        tagline="Earth's cratered companion",
        radius_km=1737.4,
        min_zoom=0,
        max_zoom=8,
        layer=MOON_LAYER,
        attribution="NASA/JPL/USGS · Moon Trek",
        attribution_url="https://trek.nasa.gov/moon/",
        tile_url_template=(
            "https://trek.nasa.gov/tiles/Moon/EQ/"
            "LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/"
            "default/default028mm/{z}/{y}/{x}.jpg"
        ),
    ),
    "mars": BodyInfo(
        id="mars",
        name="Mars",
        tagline="The red planet's rugged frontier",
        radius_km=3389.5,
        min_zoom=0,
        max_zoom=7,
        layer=MARS_LAYER,
        attribution="NASA/JPL/USGS · Mars Trek",
        attribution_url="https://trek.nasa.gov/mars/",
        tile_url_template=(
            "https://trek.nasa.gov/tiles/Mars/EQ/"
            "Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/"
            "default/default028mm/{z}/{y}/{x}.jpg"
        ),
    ),
}
