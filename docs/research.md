# Research notes

Facts gathered while building the mod, with sources. OSM snapping in `pois.py` corrects the
approximate coordinates in `config.POIS` whenever the feature is mapped with its name or
civic address.

## Project Zomboid mapping formats (verified against the tool sources)

| Fact | Source |
| --- | --- |
| BuildingEd `.tbx`: `<building version="3">`, root tile slots `ExteriorWall, ExteriorWallTrim, Door, DoorFrame, Window, Curtains, Shutters, Stairs, RoofCap, RoofSlope, RoofTop, GrimeWall`; room slots `InteriorWall, InteriorWallTrim, Floor, GrimeFloor, GrimeWall`; room `Color="r g b"` | [buildingwriter.cpp](https://github.com/timbaker/tiled/blob/zomboid/src/tiled/BuildingEditor/buildingwriter.cpp), [buildingtemplates.cpp](https://github.com/timbaker/tiled/blob/zomboid/src/tiled/BuildingEditor/buildingtemplates.cpp) |
| Tile entry indices are 1-based (0 = none); furniture indices are 0-based; furniture tiles use `<tile x y name>`; rooms grid is 1-based CSV | [buildingreader.cpp](https://github.com/timbaker/tiled/blob/zomboid/src/tiled/BuildingEditor/buildingreader.cpp) |
| Wall sheet offsets West 0, North 1, NorthWest 2, SouthEast 3, WestWindow 8, NorthWindow 9, WestDoor 10, NorthDoor 11; doors 0-3; stairs 0-2 / 8-10; curtains W0 E1 N2 S3 | [buildingtiles.cpp](https://github.com/timbaker/tiled/blob/zomboid/src/tiled/BuildingEditor/buildingtiles.cpp) |
| Category names `exterior_walls`, `interior_walls`, `exterior_wall_trim`, `interior_wall_trim` | [buildingtiles.h](https://github.com/timbaker/tiled/blob/zomboid/src/tiled/BuildingEditor/buildingtiles.h) |
| Roof types incl. `FlatTop`; depths `Zero, Point5, One, OnePoint5, Two, TwoPoint5, Three`; stairs occupy 5 tiles; door `dir N` sits on the north edge of (x,y) | [buildingobjects.cpp](https://github.com/timbaker/tiled/blob/zomboid/src/tiled/BuildingEditor/buildingobjects.cpp) |
| `.pzw`: `<world version="1.0">`, `BMPToTMX`/`GenerateLots`/`LuaSettings` as child elements with `path`/`checked` attributes, `bmp` with path/x/y/width/height, paths relative to the .pzw, lots with cell-relative x/y | [worldwriter.cpp](https://github.com/timbaker/pzworlded/blob/master/src/editor/worldwriter.cpp), [worldreader.cpp](https://github.com/timbaker/pzworlded/blob/master/src/editor/worldreader.cpp), [lotfilesmanager.cpp](https://github.com/timbaker/pzworlded/blob/master/src/editor/lotfilesmanager.cpp) |
| Default Rules.txt colours: grass 90/100/35, 117/117/47, 145/135/60; sand 210/200/160; light asphalt 165/160/140; dark asphalt 100/100/100; medium 120/120/120; gravel dirt 140/70/15; dirt 120/70/20; dirt-grass 80/55/20; potholes 110/100/100 and 130/120/120; water 0/138/255. Vegetation: trees 255/0/0, dense trees 200/0/0, trees+grass 127/0/0, fir 64/0/0, grass 0/255/0, grass+few trees 0/128/0, bushes/grass/few trees 255/0/255, bushes 200/0/200, 150/0/200, 100/0/200, corn 255/128/0 and 220/100/0. Vegetation rules only apply on grass-coloured base pixels | [pzworlded/Rules.txt](https://github.com/timbaker/pzworlded/blob/master/Rules.txt) |
| BuildingFurniture.txt: `group { label }` > `furniture { layer, corners }` > `entry { orient = W|N|E|S|SW|NW|NE|SE, x,y = tile }` | [furnituregroups.cpp](https://github.com/timbaker/tiled/blob/zomboid/src/tiled/BuildingEditor/furnituregroups.cpp) |
| Maintained Windows build of the tools; `.tbx` is an authoring format; no headless mode | [PZ_Mapping_Tools](https://github.com/Unjammer/PZ_Mapping_Tools) |
| Maps with `worldmap.xml` support the in-game map; cells are `X_Y.lotheader`, `world_X_Y.lotpack`, `chunkdata_X_Y.bin` | [Steam workshop discussion](https://steamcommunity.com/workshop/filedetails/discussion/2802508333/3273564019259903328) |
| `parkingstall` is the common vehicle zone; VehicleZoneDistribution keys match zone names | [Steam workshop](https://steamcommunity.com/sharedfiles/filedetails/comments/2939143319) |

## South-eastern New Brunswick

| Fact | Used for | Source |
| --- | --- | --- |
| Codiac Regional RCMP moved to a new detachment at 199 Albert St, Moncton; former HQ 520 Main St; satellite at 795 Main St | police POIs, vehicle zones | [CTV](https://www.ctvnews.ca/atlantic/new-brunswick/article/codiac-rcmp-opens-new-detachment-in-moncton/), [RCMP](https://rcmp-grc.gc.ca/detach/en/d/414) |
| Shediac RCMP detachment: 77 Ohio Rd | police POI | [RCMP](https://www.rcmp-grc.gc.ca/detach/en/d/427) |
| Moncton Fire Department: five stations at 299 Botsford St (No. 3, opened 2009), 72 Brandon St, 80 Caledonia Rd (No. 1), 99 Hildegarde Dr (No. 5), 800 St. George Blvd (No. 2) | fire POIs, fire vehicle zones | [City of Moncton](https://moncton.ca/my-govt-work-public-safety/moncton-fire-department) |
| Tidal bore on the Petitcodiac twice daily; causeway built 1968, gates opened 2010 and the bore is recovering | river / mud flats | [moncton.ca](https://moncton.ca/attractions), [Parks Canada](https://www.pc.gc.ca/apps/DFHD/page_nhs_eng.aspx?id=1511) |
| Magnetic Hill, Magnetic Hill Zoo, Magic Mountain, Casino NB cluster at the NW edge of Moncton; Resurgo Place houses the Moncton Museum and Transportation Discovery Centre | landmark POIs | [planetware](https://www.planetware.com/tourist-attractions-/moncton-cdn-nb-nbm.htm) |
| World's Largest Lobster, Shediac: 90-ton sculpture by Winston Bronnum, 11 m long, 5 m high, at the western entrance to town; Parlee Beach has some of the warmest salt water north of Virginia | Shediac POIs | [smartertravel](https://www.smartertravel.com/things-shediac-canada/) |
| Hopewell Rocks: flowerpot columns up to 15 m, walkable at low tide, on Route 114 about 40 km NE of Fundy National Park; Cape Enrage: 50 m cliffs and lighthouse on Route 915; Fundy Coastal Drive Route 915 Alma to Riverside-Albert 60 km | southern areas and corridors | [Frommer's](https://www.frommers.com/destinations/fundy-national-park/side-trips/), [Albert County Museum](https://www.albertcountymuseum.com/getting-here) |
| Hillsborough sits on a hill over the Petitcodiac near Routes 910 and 114; Battle of Petitcodiac (1755) plaque | Hillsborough POI | [Wikipedia](https://en.wikipedia.org/wiki/Hillsborough,_New_Brunswick), [hmdb](https://www.hmdb.org/m.asp?m=106630) |
| Havelock parish named for Henry Havelock, erected 1859 | flavour | [Wikipedia](https://en.wikipedia.org/wiki/Havelock_Parish,_New_Brunswick) |
| Acadian forest: red spruce characteristic with balsam fir, yellow birch, sugar maple; red/white pine and hemlock minor; uplands lean hardwood, poorly drained sites lean spruce/birch; a Riverside-Albert property has 32 species, mostly 80+ years old | vegetation mix (softwood on wet/low noise, hardwood on uplands) | [UMaine CRSF](https://crsf.umaine.edu/resource/1-acadian-spruce-fir-resource), [CTV](https://atlantic.ctvnews.ca/conservancy-group-to-protect-one-of-last-acadian-forests-in-maritimes-1.3930441) |

Wikipedia itself was unreachable from the build container, so coordinates in `config.POIS` are
from memory and rely on OSM snapping; the civic addresses above are the authoritative anchors.
