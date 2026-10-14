"""Lon/lat <-> Zomboid tile coordinates."""
from __future__ import annotations

import math
from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _transformer():
    from pyproj import Transformer

    return Transformer.from_crs("EPSG:4326", config.PROJECTION, always_xy=True)


@lru_cache(maxsize=1)
def origin_en() -> tuple[float, float]:
    """Projected easting/northing of the world origin, snapped to a whole cell."""
    e, n = _transformer().transform(config.ORIGIN_LON, config.ORIGIN_LAT)
    return math.floor(e / config.CELL) * config.CELL, math.ceil(n / config.CELL) * config.CELL


def lonlat_to_tile(lon: float, lat: float) -> tuple[float, float]:
    e, n = _transformer().transform(lon, lat)
    e0, n0 = origin_en()
    return (e - e0) + config.CELL_OFFSET_X * config.CELL, (n0 - n) + config.CELL_OFFSET_Y * config.CELL


def tile_to_cell(x: float, y: float) -> tuple[int, int]:
    return int(x // config.CELL), int(y // config.CELL)


def tile_to_lonlat(x: float, y: float) -> tuple[float, float]:
    from pyproj import Transformer

    inv = Transformer.from_crs(config.PROJECTION, "EPSG:4326", always_xy=True)
    e0, n0 = origin_en()
    e = x - config.CELL_OFFSET_X * config.CELL + e0
    n = n0 - (y - config.CELL_OFFSET_Y * config.CELL)
    return inv.transform(e, n)
