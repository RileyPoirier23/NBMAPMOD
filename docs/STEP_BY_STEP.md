# Step by step: from this repo to playing in Moncton

Assumes Windows with Steam. Times are rough; the Moncton render and the WorldEd passes are
the long parts and can run unattended.

## 1. Install the tools (15 min)

1. Install **Python 3.11 or newer** from python.org. Tick "Add python.exe to PATH".
2. Install **Git for Windows** (git-scm.com).
3. Get the **mapping tools**: Steam > Library > Tools > "Project Zomboid Mapping Tools",
   or the maintained community build at https://github.com/Unjammer/PZ_Mapping_Tools
   (Releases, unzip anywhere). You get WorldEd, TileZed and BuildingEd.
4. Open **TileZed** once: Tools > Tilesets > Add Tiles, point it at
   `C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media\texturepacks`
   (or the 1x/2x tiles folder the tools' README names). Do the same in BuildingEd
   (Tiles > Tiles). This is what makes tile names resolve.

## 2. Get the repo (2 min)

```bat
cd %USERPROFILE%\Documents
git clone -b claude/nice-fermi-x6zuhs https://github.com/RileyPoirier23/NBMAPMOD.git
cd NBMAPMOD
pip install -r tools\requirements.txt
```

## 3. Smoke test (1 min)

```bat
python tools\tests\test_pipeline.py
```
Should end with `ok: 19 buildings, 23 cells`.

## 4. Download the OpenStreetMap data (10-30 min, needs internet)

```bat
cd tools
pip install osmium
python -m nbmap fetch --geofabrik
```
Downloads the whole New Brunswick extract once (about 60 MB) from Geofabrik and filters every
area out of it locally into `tools\data\osm\`. This is the reliable route.

Alternative without the extra package: `python -m nbmap fetch` queries the Overpass API tile by
tile. Overpass answers "504 busy" when it is overloaded; the script retries, but if it keeps
failing use the Geofabrik route above. Existing files are skipped on re-runs.

## 5. Furniture library (2 min, do this before the big build)

```bat
python -m nbmap furniture --tilezed "C:\path\to\the\mapping\tools"
```
Reads `BuildingFurniture.txt` from your tools so every building gets furnished with tiles
BuildingEd already knows. Skip it and buildings come out as empty shells.

## 6. Preview one chunk first (5 min)

```bat
python -m nbmap build --chunk 46,16
```
Chunk numbers are cell/5. Downtown Moncton is around cell 233,83, so chunk 46,16. Open
`tools\build\bmp\chunk_230_80.png` and `..._veg.png` in any image viewer. Roads, water,
forest and fields should be recognisable. Then open one file from `tools\build\buildings\`
in BuildingEd. If BuildingEd flags a tile as missing, fix the name in
`tools\nbmap\data\themes.json` and rebuild.

## 7. Full build (1-2 h unattended)

```bat
python -m nbmap build
```
Writes `tools\build\`: bitmaps, ~30,000 buildings, `NewBrunswick.pzw`, Rules/Blends,
`zombie_spawn_map.png`, `POIS.md` and the mod folder skeleton.

## 8. WorldEd (1-3 h, mostly waiting)

1. WorldEd > File > Open > `tools\build\NewBrunswick.pzw`.
2. File > BMP to TMX > check the settings dialog shows Rules.txt / Blends.txt / MapBaseXML.txt
   from the build folder, then **All Cells**. One TMX per cell lands in `export_tmx\`.
3. File > Generate Lots > **All Cells**. Output goes to
   `tools\build\mod\NBMap_Moncton\media\maps\Moncton, NB\` (pre-set). If WorldEd asks for the
   TileDef folder, point it at the game's `media\` folder.
4. Optional: File > Generate In-Game Map Image if you want the vanilla-style map image; the
   `worldmap.xml` with street names is already in the mod folder.

If WorldEd refuses the project file, create a new world (236 x 86 cells), then in
BMP to TMX settings add each image from `tools\build\bmp\` at the x/y listed in
`NewBrunswick.pzw`. The lots can be re-added by cell from `tools\build\lots.json`.

## 9. Install and play (5 min)

1. Copy `tools\build\mod\NBMap_Moncton` to `%USERPROFILE%\Zomboid\mods\`.
2. Launch Project Zomboid > Mods > enable it. New game > spawn region "Moncton, NB".
3. Press M for the map: every street carries its name, landmarks are labelled.

## 10. RCMP mod (5 min)

```bat
cd %USERPROFILE%\Documents\NBMAPMOD
python tools\rcmp\make_rcmp.py --pz-dir "C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid" --out mods\RCMP_NB --preview-layout
```
Copy `mods\RCMP_NB` to `%USERPROFILE%\Zomboid\mods\` and enable it. The `*_layout.png`
files show a labelled grid over each texture; move the boxes in `tools\rcmp\decals.json`
onto the doors / legs / hat and re-run without `--preview-layout`.

## 11. Improving buildings later

Open any `tools\build\buildings\*.tbx` in BuildingEd, edit, save, then in WorldEd
right-click that cell > Generate Lots, and copy the mod folder again.

## If something goes wrong

* `BMP to TMX failed ... blends_natural_01_xx`: tilesets not loaded in TileZed (step 1.4).
* Out of memory in WorldEd: run BMP to TMX a few cells at a time (select cells, right-click).
* Empty rooms: step 5 was skipped.
* A town missing: its OSM file failed to download; re-run `python -m nbmap fetch`.
