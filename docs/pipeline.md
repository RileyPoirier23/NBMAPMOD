# Generator pipeline

```
data/osm/*.json  ──osm.py──▶  Feature(shapely geom in tiles, tags)
                                   │
        ┌──────────────┬───────────┼─────────────┬──────────────┐
   render.py      buildings.py   zones.py    worldmap.py     pzw.py
   bmp/*.png      buildings/*.tbx objects.lua worldmap.xml   NewBrunswick.pzw
   (base + veg)   lots.json       spawnpoints zombie map     Rules.txt
```

* `geo.py` – EPSG:32620 projection, world origin snapped to a cell, cell offset so the mod
  never overlaps vanilla Knox Country cells.
* `render.py` – per 5x5-cell chunk: ground (landuse, water, rail, sidewalks, shoulders, roads,
  potholes) then vegetation (forest interior/edge/species, scrub, wetland, meadow, orchard,
  crops, parks, yards, wild Acadian forest, mapped trees, hedges) with everything cleared
  under roads, buildings, water and hard surfaces. Noise is seeded by world tile so chunk
  boundaries are invisible.
* `buildings.py` – footprint -> tile mask -> BSP rooms -> doors/windows/stairs/roof -> `.tbx`.
* `zones.py` – objects.lua zones, vehicle zones, spawn points, zombie density image.
* `worldmap.py` – in-game map features with OSM names, addresses and place labels.
* `pzw.py` – WorldEd project listing every bitmap and every lot at its world position.

Only cells within one cell of a road or building are generated (plus the corridors), which keeps
the 58 km x 28 km bounding box down to the cells people can actually reach.
