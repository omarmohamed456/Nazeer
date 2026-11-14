from pathlib import Path

OUT = Path("out")
MAPDIR = Path("mappings")
STEP_DEG = 10
CHUNK = 100_000

BODIES = {
    "mars": {
        "path": Path(r"E:\NASA\sim3292_database\SIM3292_Shapefiles\SIM3292_Global_Geology.shp"),
        "layer": None,
        "radius_m": 3_396_190.0,
        "fields": {"unit": "Unit", "name": "UnitDesc"},
    },
    "moon": {
        "path": Path(r"E:\NASA\Unified_Geologic_Map_of_the_Moon_GIS_v2\Lunar_GIS\Shapefiles\GeoUnits.shp"),
        "layer": "GeoUnits",
        "radius_m": 1_737_400.0,
        "fields": {"unit": "FIRST_Unit", "name": "FIRST_Un_1", "age": "FIRST_Un_2"},
    },
    "earth": {
        "path": Path(r"E:\NASA\LiMW_GIS 2015.gdb"),
        "layer": None,
        "radius_m": 6_371_007.181,
        "make_valid": False,
        "fields": {"unit": "xx", "name": "Litho"},
    },
}