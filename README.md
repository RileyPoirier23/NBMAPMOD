# NBMAPMOD - New Brunswick for Project Zomboid

Two mods for Project Zomboid (Build 41):

| Folder | What it is |
| --- | --- |
| `tools/nbmap` | Generator that turns OpenStreetMap data into a 1:1 map of **Moncton / Dieppe / Riverview, Salisbury, Petitcodiac and Havelock** plus the Route 2 / 106 / 112 / 880 corridors that join them. Output is a ready-to-open WorldEd project and the mod folder (`NBMap_Moncton`). |
| `mods/RCMP_NB` + `tools/rcmp` | Reskin mod that turns Knox County police into the **RCMP**: white cruisers, grey duty shirts, breeches, forage caps, bullet vests, plus the red serge and Stetson dress uniform. |

Everything is generated from open data and from your own copy of the game, so nothing
copyrighted by The Indie Stone or by map providers is stored in this repository.

## How the map is 1:1

* OSM coordinates are projected with UTM zone 20N, where 1 m = 1 Zomboid tile. A street that is
  7.3 m wide in Moncton is 7 tiles wide in game; a house with a 9 x 12 m footprint is a 9 x 12
  tile building standing on the exact spot. Scale error over the whole 58 km span is below 0.1 %.
* Every `highway` way becomes a road of the right class and width (lanes, shoulders, sidewalks in
  built-up areas, gravel where OSM says unpaved) and appears on the in-game map **with its real
  name** through `worldmap.xml`.
* Every OSM building becomes a BuildingEd `.tbx` with its real footprint, storeys from
  `building:levels`, a front door facing its street, windows, stairs and rooms typed from OSM
  tags (`shop=supermarket` -> grocery rooms, `amenity=police` -> police storage, ...). Room
  types drive vanilla loot, zombie outfits and vehicle zones (police cruisers at the Codiac RCMP
  detachment, fire trucks at the fire halls, parking stalls on every lot and driveway).
* Vegetation is detailed per tile: mapped forest polygons get dense interiors, thinner bushy
  edges and a softwood/hardwood split (from `leaf_type` where mapped, otherwise 55 % softwood as
  in the real Acadian forest); scrub, marsh reeds on the Petitcodiac wetlands, meadows with tall
  grass and wildflowers, orchards in rows, crop rows in farm fields with grassy margins, parks and
  cemeteries with scattered trees, hedges, individual mapped trees, yard trees and bushes around
  houses. Unmapped land between communities is filled with noise-driven Acadian forest and
  clearings, so the drive from Havelock to Moncton is through real bush.
* Water: the Petitcodiac, Jones Lake, every mapped pond and stream.
* `objects.lua` zones: TownZone, Forest / DeepForest / Vegitation (foraging), FarmLand, trailer
  parks, vehicle zones (parking, police, fire, medical, farm, car dealers, junkyards, Trans-Canada
  traffic jams). Spawn points in every community snap to a real house.
* A zombie spawn map weights downtown Moncton and the commercial strips heaviest, suburbs
  medium, farms and forest light.

## Build the map

Requirements: Python 3.10+, internet for the OSM download (about 150 MB), TileZed + WorldEd
(the official Project Zomboid mapping tools), and about 10 GB of disk for the Moncton cells.

```bash
pip install -r tools/requirements.txt
cd tools
python -m nbmap fetch            # downloads OSM data for all seven areas into data/osm/
python -m nbmap build            # renders everything into build/
```

Then follow `build/README_WORLDED.txt`: open `build/NewBrunswick.pzw` in WorldEd, run
*BMP to TMX* and *Generate Lots*, copy `build/mod/NBMap_Moncton` into `Zomboid/mods/`.

Build time is dominated by Moncton: expect ~2,700 cells, ~30,000 buildings and roughly an hour of
rendering on a laptop, then another hour inside WorldEd. Use `--chunk kx,ky` to preview one
5x5-cell chunk first. The smoke test (`python tools/tests/test_pipeline.py`) runs the whole
pipeline offline on a synthetic town.

### What still needs a human

* **Interiors.** Generated buildings are correct shells with rooms, doors, windows, stairs and a
  flat roof, but no furniture (furniture is where loot containers live). Open any
  `build/buildings/*.tbx` in BuildingEd, furnish it, and rebuild lots. `tools/nbmap/data/furniture.json`
  is the hook for an auto-furnishing library once you have verified tile names in BuildingEd.
* **Roof shapes, rails, bridge decks, power lines** need TileZed objects; the generator marks
  the ground for them.
* **Tile names.** `tools/nbmap/data/Rules.txt` and `data/themes.json` use vanilla B41 tile
  sheet names. If your TileZed flags any as missing, fix the name in those two files and
  rebuild; every building and ground tile updates at once.
* **Formats.** The `.pzw` and `.tbx` writers follow TileZed's XML formats; they have been checked
  for well-formedness but not opened in the GUI from this repository. If WorldEd rejects the
  project, the fallback is in `README_WORLDED.txt` (create a world and add the `bmp/` images;
  their positions are listed in the `.pzw`).

Tunables (areas, palette, road widths, vegetation density, building themes, zombie density,
spawn points) are all in `tools/nbmap/config.py`.

## Build the RCMP mod

```bash
python tools/rcmp/make_rcmp.py --pz-dir "C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid" --out mods/RCMP_NB
```

The script reads your vanilla scripts, textures and clothing XML, so it tracks game updates:

* police vehicle textures are recoloured to the white RCMP livery at their vanilla paths (every
  Chevalier Nyala / pickup police variant becomes an RCMP cruiser, no vehicle script edits);
* new items `Shirt_RCMPGrey`, `Tshirt_RCMPGrey`, `Trousers_RCMP`, `Vest_BulletRCMP`,
  `Hat_RCMPForage`, `Hat_RCMPRiot`, `Jacket_RCMPSerge`, `Hat_RCMPStetson` with recoloured textures,
  clothing XML and GUID table;
* outfits `RCMP`, `RCMPRiot`, `RCMPSerge`; the Lua in `media/lua/server` re-points every police
  zombie zone at them and adds the uniforms to police station containers.

The recolour is a solid starting point, not pixel art: hand-paint the stripe, the RCMP crest and
the yellow breech stripe over the PNGs in `mods/RCMP_NB/media/textures` for the full effect.
Those generated files are git-ignored because they derive from the game's own assets.

## Data licence

Map data (c) OpenStreetMap contributors, ODbL. Keep the attribution in `mod.info` if you
publish to the Workshop.
