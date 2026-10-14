# NBMAPMOD - New Brunswick for Project Zomboid

Two mods for Project Zomboid (Build 41). Coverage: Moncton, Dieppe, Riverview, Shediac and Parlee Beach, Salisbury, Petitcodiac, Havelock, Hillsborough, Hopewell Rocks, Riverside-Albert, Cape Enrage, Alma and Fundy National Park, with the highways between them.

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
* Water: the Petitcodiac, Jones Lake, Shediac Bay, every mapped pond and stream.
* Points of interest named on the in-game map and snapped to their real OSM building or civic
  address: Magnetic Hill, the Avenir Centre, Resurgo Place, Bore View Park, both hospitals, the
  universities, the new Codiac RCMP detachment on Albert Street and the old one on Main, all five
  Moncton fire halls, the airport, CF Champlain, the World's Largest Lobster, Parlee Beach,
  Pointe-du-Chene wharf, Hopewell Rocks, Cape Enrage, Alma and Fundy National Park, and more
  (`build/POIS.md` lists them with their tile coordinates). Sources are in `docs/research.md`.
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

* **Interiors are furnished automatically once you give the generator a furniture library.**
  Furniture is where loot containers live, so this matters. Harvest the library from your own
  tools so every tile name is one BuildingEd already knows:

  ```bash
  cd tools
  python -m nbmap furniture --tilezed "C:/path/to/TileZed"      # reads TileZed's BuildingFurniture.txt palette
  python -m nbmap furniture --tbx "C:/path/to/some/buildings"   # or learn from any existing .tbx buildings
  python -m nbmap build --skip-render                           # rebuilds every .tbx with furniture
  ```

  The placement rules in `tools/nbmap/furnish.py` put beds, wardrobes, fridges, stoves, counters
  and sinks, toilets and baths, sofas and TVs, desks and filing cabinets, store shelves and
  registers, pews, lockers, gun cabinets and so on against the right walls, keep doorways and
  stairs clear, and match furniture to each room by its vanilla room type (bedroom, kitchen,
  grocery, pharmacy, policestorage, ...). Without a library the buildings are empty shells.
* **Roof shapes, rails, bridge decks, power lines** need TileZed objects; the generator marks
  the ground for them.
* **Tile names.** `tools/nbmap/data/Rules.txt` and `data/themes.json` use vanilla B41 tile
  sheet names. If your TileZed flags any as missing, fix the name in those two files and
  rebuild; every building and ground tile updates at once.
* **Formats.** The `.pzw` and `.tbx` writers were checked line by line against the TileZed and
  WorldEd source (see `docs/research.md`), and the build ships WorldEd's own default
  `Rules.txt`, `Blends.txt` and `MapBaseXML.txt` with New Brunswick vegetation rules appended,
  so the images use the stock colour table. They have not yet been opened in the GUI from this
  repository; if anything is refused, `README_WORLDED.txt` has the manual fallback.

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
