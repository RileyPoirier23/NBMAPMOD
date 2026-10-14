"""Build a small synthetic Overpass-style JSON near downtown Moncton for offline tests."""
import json
import sys
from pathlib import Path

lat0, lon0 = 46.0880, -64.7800   # Main St / Botsford St area
dlat, dlon = 1 / 111320.0, 1 / (111320.0 * 0.6947)   # ~1 m


def n(nid, x, y):
    return {"type": "node", "id": nid, "lat": lat0 - y * dlat, "lon": lon0 + x * dlon}


nodes, ways, nid, wid = [], [], 1, 1000


def way(pts, tags, close=False):
    global nid, wid
    ids = []
    for x, y in pts:
        nodes.append(n(nid, x, y))
        ids.append(nid)
        nid += 1
    if close:
        ids.append(ids[0])
    ways.append({"type": "way", "id": wid, "nodes": ids, "tags": tags})
    wid += 1


way([(0, 100), (600, 100)], {"highway": "primary", "name": "Main Street", "lanes": "4"})
way([(300, -50), (300, 500)], {"highway": "residential", "name": "Botsford Street"})
way([(0, 300), (600, 300)], {"highway": "tertiary", "name": "Queen Street"})
way([(0, 420), (600, 430)], {"highway": "trunk", "name": "Trans-Canada Highway", "ref": "2"})
way([(150, 100), (150, 300)], {"highway": "service"})
way([(450, 300), (450, 480)], {"highway": "track", "surface": "gravel"})
way([(0, 0), (600, 0), (600, 60), (0, 60)], {"landuse": "commercial"}, close=True)
way([(0, 130), (600, 130), (600, 280), (0, 280)], {"landuse": "residential"}, close=True)
way([(0, 330), (280, 330), (280, 400), (0, 400)], {"landuse": "forest", "leaf_type": "needleleaved"}, close=True)
way([(320, 330), (600, 330), (600, 400), (320, 400)], {"natural": "wood"}, close=True)
way([(0, 460), (600, 460), (600, 600), (0, 600)], {"landuse": "farmland"}, close=True)
way([(480, 150), (590, 150), (590, 260), (480, 260)], {"leisure": "park", "name": "Victoria Park"}, close=True)
way([(380, 150), (470, 150), (470, 270), (380, 270)], {"natural": "wetland"}, close=True)
way([(100, 480), (250, 480), (250, 580), (100, 580)], {"natural": "water", "name": "Jones Lake"}, close=True)
way([(0, 540), (600, 560)], {"waterway": "stream", "name": "Halls Creek"})
way([(0, 520), (600, 520)], {"railway": "rail", "name": "CN"})
way([(20, 10), (120, 10), (120, 50), (20, 50)], {"building": "retail", "shop": "supermarket", "name": "Sobeys"}, close=True)
way([(140, 10), (200, 10), (200, 50), (140, 50)], {"building": "yes", "amenity": "police", "name": "Codiac RCMP"}, close=True)
way([(220, 10), (260, 10), (260, 40), (220, 40)], {"building": "commercial", "amenity": "restaurant"}, close=True)
way([(20, 6), (120, 6), (120, 50), (20, 50)], {"amenity": "parking"}, close=True)
for i in range(6):
    x = 20 + i * 48
    way([(x, 150), (x + 12, 150), (x + 12, 162), (x, 162)], {"building": "house", "addr:housenumber": str(100 + i), "addr:street": "Main Street"}, close=True)
    way([(x, 200), (x + 10, 200), (x + 10, 214), (x, 214)], {"building": "house", "building:levels": "2"}, close=True)
way([(330, 160), (370, 160), (370, 190), (330, 190)], {"building": "apartments", "building:levels": "3"}, close=True)
way([(330, 220), (338, 220), (338, 226), (330, 226)], {"building": "shed"}, close=True)
way([(330, 240), (345, 240), (345, 262), (330, 262)], {"building": "church", "amenity": "place_of_worship"}, close=True)
# an L-shaped school
way([(400, 20), (470, 20), (470, 40), (430, 40), (430, 60), (400, 60)], {"building": "school", "amenity": "school", "name": "Moncton High"}, close=True)
nodes.append({"type": "node", "id": 9999, "lat": lat0 - 250 * dlat, "lon": lon0 + 200 * dlon, "tags": {"natural": "tree"}})
nodes.append({"type": "node", "id": 9998, "lat": lat0 - 90 * dlat, "lon": lon0 + 300 * dlon, "tags": {"place": "city", "name": "Moncton"}})

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests_fixture")
out.mkdir(parents=True, exist_ok=True)
(out / "moncton.json").write_text(json.dumps({"elements": nodes + ways}))
print(out / "moncton.json")
