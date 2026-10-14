"""All tunables for the New Brunswick map generator live here.

Coordinates: Project Zomboid tiles are 1 m squares. World x grows east, world y grows
south. A cell is 300x300 tiles. We project OSM lon/lat with UTM zone 20N (EPSG:32620),
which covers all of south-eastern New Brunswick with <0.1 % scale error, so the map is
1:1 with the real ground.
"""
from __future__ import annotations

from dataclasses import dataclass, field

CELL = 300
CHUNK_CELLS = 5                     # one WorldEd bitmap = CHUNK_CELLS x CHUNK_CELLS cells
PROJECTION = "EPSG:32620"           # UTM 20N

# World origin (top-left) in lon/lat. Everything east/south of this gets positive tile coords.
# Chosen so the whole Havelock -> Moncton/Dieppe corridor fits.
ORIGIN_LON = -65.42
ORIGIN_LAT = 46.30                  # north of Parlee Beach / Shediac

# Cell offset so the mod never collides with vanilla Knox Country cells (which end near x=60).
CELL_OFFSET_X = 70
CELL_OFFSET_Y = 0


@dataclass
class Area:
    key: str
    title: str
    south: float
    west: float
    north: float
    east: float
    # how many cells around roads/buildings to keep (forest fill)
    halo_cells: int = 1

    @property
    def bbox(self) -> str:
        return f"{self.south},{self.west},{self.north},{self.east}"


# The four requested communities plus the Route 2 / Route 106 / Route 112 / Route 880
# corridors that physically connect them, so the world is one contiguous road network.
AREAS: list[Area] = [
    Area("moncton", "Moncton, Dieppe & Riverview", 46.030, -64.930, 46.175, -64.630, 1),
    Area("salisbury", "Salisbury", 46.020, -65.085, 46.070, -65.005, 1),
    Area("petitcodiac", "Petitcodiac", 45.920, -65.215, 45.965, -65.140, 1),
    Area("havelock", "Havelock", 45.970, -65.385, 46.005, -65.315, 1),
    Area("corridor_moncton_salisbury", "Route 2/106 Moncton-Salisbury", 46.020, -65.010, 46.110, -64.925, 0),
    Area("corridor_salisbury_petitcodiac", "Route 2/106 Salisbury-Petitcodiac", 45.930, -65.145, 46.045, -65.080, 0),
    Area("corridor_petitcodiac_havelock", "Route 880 Petitcodiac-Havelock", 45.955, -65.320, 46.000, -65.210, 0),
    # east: Shediac, Parlee Beach and Pointe-du-Chene via Route 15 / Route 133
    Area("shediac", "Shediac, Parlee Beach & Pointe-du-Chene", 46.190, -64.600, 46.260, -64.480, 1),
    Area("corridor_dieppe_shediac", "Route 15/133 Dieppe-Shediac", 46.100, -64.660, 46.200, -64.560, 0),
    # south: Route 114 down the Petitcodiac to Hillsborough, Hopewell Rocks, Riverside-Albert,
    # then Route 915 past Cape Enrage to Alma and Fundy National Park
    Area("hillsborough", "Hillsborough", 45.900, -64.680, 45.960, -64.620, 1),
    Area("corridor_riverview_hillsborough", "Route 114 Riverview-Hillsborough", 45.955, -64.760, 46.040, -64.640, 0),
    Area("hopewell", "Hopewell Cape & Hopewell Rocks", 45.800, -64.620, 45.880, -64.540, 1),
    Area("corridor_hillsborough_hopewell", "Route 114 Hillsborough-Hopewell", 45.875, -64.660, 45.905, -64.560, 0),
    Area("riverside_albert", "Riverside-Albert", 45.720, -64.780, 45.780, -64.700, 1),
    Area("corridor_hopewell_riverside", "Route 114 Hopewell-Riverside-Albert", 45.775, -64.760, 45.805, -64.560, 0),
    Area("cape_enrage", "Cape Enrage", 45.580, -64.800, 45.640, -64.760, 1),
    Area("corridor_riverside_alma", "Route 915/114 Riverside-Albert-Alma", 45.590, -64.960, 45.725, -64.740, 0),
    Area("alma_fundy", "Alma & Fundy National Park", 45.560, -65.020, 45.640, -64.900, 1),
]

MOD_ID = "NBMap_Moncton"
MOD_NAME = "New Brunswick: Moncton, Shediac, Fundy & Hopewell Rocks"
MAP_FOLDER = "Moncton, NB"          # media/maps/<MAP_FOLDER>
MOD_FOLDER_SAFE = MAP_FOLDER        # used inside relative paths written to the .pzw

# ---------------------------------------------------------------- WorldEd base-image palette
# These are the exact colours of WorldEd's default Rules.txt (pzworlded/Rules.txt), so the
# images work with a stock TileZed install. See data/worlded/Rules.txt.
C = {
    "grass_dark":     (90, 100, 35),     # darkgrass
    "grass_medium":   (117, 117, 47),    # medgrass
    "grass_light":    (145, 135, 60),    # lightgrass
    "sand":           (210, 200, 160),   # sand
    "dirt":           (120, 70, 20),     # dirt
    "dirt_gravel":    (140, 70, 15),     # gravel dirt (floors_exterior_natural_01_12)
    "asphalt_dark":   (100, 100, 100),   # street2 - main roads
    "asphalt_medium": (120, 120, 120),   # street
    "asphalt_light":  (165, 160, 140),   # lightgravel - sidewalks, lots, light asphalt
    "pothole_dark":   (110, 100, 100),
    "pothole_light":  (130, 120, 120),
    "water":          (0, 138, 255),
    "concrete":       (165, 160, 140),   # sidewalks use the light asphalt tiles
    "mud":            (80, 55, 20),      # dirtgrass - tidal flats, marsh ground
    "crop_rows":      (120, 70, 20),     # ploughed rows are plain dirt; crops go on the veg layer
}

# ---------------------------------------------------------------- WorldEd vegetation-image palette
# Default WorldEd vegetation colours (they only apply where the base pixel is one of the
# three grass colours; marsh reeds also apply on dirtgrass) plus NB extras defined in
# data/worlded/Rules_nb_extra.txt.
V = {
    "none":           (0, 0, 0),
    "forest_dense":   (200, 0, 0),      # "Dense Trees + grass"
    "forest":         (255, 0, 0),      # "Trees"
    "forest_light":   (127, 0, 0),      # "Trees + grass"
    "conifer_dense":  (255, 64, 0),     # NB extra: spruce/fir stand, dense
    "conifer":        (200, 64, 0),     # NB extra: spruce/fir stand
    "fir_sparse":     (64, 0, 0),       # "Fir Trees + grass" (default rule)
    "bushes":         (150, 0, 200),    # "Bushes & Grass"
    "bushes_dense":   (200, 0, 200),    # "Dense Bushes & Grass"
    "bushes_sparse":  (100, 0, 200),    # "Sparse Bushes & Grass"
    "shrubland":      (255, 0, 255),    # "Bushes, Grass, Few Trees"
    "park_scatter":   (0, 128, 0),      # "Grass + Few Trees"
    "tall_grass":     (0, 255, 0),      # "Grass (all types)"
    "wetland":        (0, 160, 160),    # NB extra: salt marsh / reeds
    "flowers":        (255, 128, 255),  # NB extra: wildflower meadow
    "crops":          (255, 128, 0),    # "Farm Corn"
    "crops2":         (220, 100, 0),    # "Farm Corn 2"
    "hedge":          (0, 80, 0),       # NB extra
}

# ---------------------------------------------------------------- road classes -> (surface width, base colour, sidewalk)
# widths are in tiles (metres) and are for a single OSM way. Divided highways are
# two ways in OSM so each carriageway gets its own strip, exactly as on the ground.
# Note: sidewalks ('concrete') and 'asphalt_light' are the same WorldEd colour.
ROADS = {
    "motorway":      dict(width=9, color="asphalt_dark", shoulder="asphalt_medium", shoulder_w=2, sidewalk=False, clear=16),
    "motorway_link": dict(width=5, color="asphalt_dark", shoulder="asphalt_medium", shoulder_w=1, sidewalk=False, clear=10),
    "trunk":         dict(width=9, color="asphalt_dark", shoulder="asphalt_medium", shoulder_w=2, sidewalk=False, clear=16),
    "trunk_link":    dict(width=5, color="asphalt_dark", shoulder="asphalt_medium", shoulder_w=1, sidewalk=False, clear=10),
    "primary":       dict(width=8, color="asphalt_dark", shoulder="asphalt_medium", shoulder_w=1, sidewalk=True, clear=8),
    "primary_link":  dict(width=5, color="asphalt_dark", shoulder=None, shoulder_w=0, sidewalk=False, clear=6),
    "secondary":     dict(width=7, color="asphalt_dark", shoulder=None, shoulder_w=0, sidewalk=True, clear=7),
    "secondary_link":dict(width=5, color="asphalt_dark", shoulder=None, shoulder_w=0, sidewalk=False, clear=6),
    "tertiary":      dict(width=7, color="asphalt_medium", shoulder=None, shoulder_w=0, sidewalk=True, clear=6),
    "tertiary_link": dict(width=5, color="asphalt_medium", shoulder=None, shoulder_w=0, sidewalk=False, clear=5),
    "unclassified":  dict(width=6, color="asphalt_medium", shoulder=None, shoulder_w=0, sidewalk=False, clear=5),
    "residential":   dict(width=6, color="asphalt_medium", shoulder=None, shoulder_w=0, sidewalk=True, clear=5),
    "living_street": dict(width=5, color="asphalt_medium", shoulder=None, shoulder_w=0, sidewalk=True, clear=4),
    "service":       dict(width=4, color="asphalt_light", shoulder=None, shoulder_w=0, sidewalk=False, clear=3),
    "track":         dict(width=3, color="dirt_gravel", shoulder=None, shoulder_w=0, sidewalk=False, clear=2),
    "path":          dict(width=2, color="dirt", shoulder=None, shoulder_w=0, sidewalk=False, clear=1),
    "footway":       dict(width=2, color="concrete", shoulder=None, shoulder_w=0, sidewalk=False, clear=1),
    "cycleway":      dict(width=3, color="asphalt_light", shoulder=None, shoulder_w=0, sidewalk=False, clear=2),
    "bridleway":     dict(width=2, color="dirt", shoulder=None, shoulder_w=0, sidewalk=False, clear=1),
    "pedestrian":    dict(width=6, color="concrete", shoulder=None, shoulder_w=0, sidewalk=False, clear=3),
    "steps":         dict(width=2, color="concrete", shoulder=None, shoulder_w=0, sidewalk=False, clear=1),
}
UNPAVED_SURFACES = {"unpaved", "gravel", "dirt", "ground", "fine_gravel", "compacted", "earth", "grass", "sand", "mud"}
SIDEWALK_WIDTH = 2
WATERWAY_WIDTHS = {"river": 10, "canal": 8, "stream": 2, "ditch": 1, "drain": 1}

# ---------------------------------------------------------------- zone sizes for objects.lua
ZONE_GRID = 50                       # resolution of auto-generated zones (tiles)
TOWN_ZONE_BUILDING_DENSITY = 2       # >= this many buildings in a ZONE_GRID block -> TownZone

# ---------------------------------------------------------------- vegetation behaviour
VEG = dict(
    forest_edge_tiles=6,             # tiles of thinner trees along a forest edge
    forest_dense_threshold=0.42,     # noise > this -> dense trees
    forest_gap_threshold=0.12,       # noise < this -> gap / bushes
    yard_tree_chance=0.012,          # residential yards
    yard_bush_chance=0.03,
    park_tree_chance=0.04,
    meadow_tallgrass_threshold=0.35,
    field_margin_tiles=3,
    conifer_fraction=0.55,           # NB Acadian forest: ~55 % softwood where OSM gives no leaf_type
    road_clear_extra=1,
    building_clear=2,
    noise_scale=18.0,
    seed=1867,                       # Confederation, obviously
)

# ---------------------------------------------------------------- building generation
BUILDINGS = dict(
    min_area=12,                     # m^2 - anything smaller is a shed (still built, 1 room)
    max_footprint=120,               # tiles - larger buildings are clipped (warehouses, malls)
    default_levels=1,
    floor_height=1,
    window_spacing=3,
    seed=1867,
)

# OSM building/amenity/shop tag -> BuildingEd room InternalName and a theme for walls/floors.
# Room internal names drive vanilla loot distributions (see ProceduralDistributions).
BUILDING_THEMES = {
    "house":        dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom", "bedroom"], theme="house"),
    "residential":  dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom"], theme="house"),
    "detached":     dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom", "bedroom"], theme="house"),
    "semidetached_house": dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom"], theme="house"),
    "apartments":   dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom", "bedroom", "kitchen"], theme="apartment"),
    "terrace":      dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom"], theme="house"),
    "bungalow":     dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom"], theme="house"),
    "cabin":        dict(rooms=["livingroom", "kitchen", "bedroom"], theme="cabin"),
    "static_caravan": dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom"], theme="trailer"),
    "garage":       dict(rooms=["garage"], theme="garage"),
    "garages":      dict(rooms=["garage"], theme="garage"),
    "shed":         dict(rooms=["shed"], theme="shed"),
    "hut":          dict(rooms=["shed"], theme="shed"),
    "barn":         dict(rooms=["barn"], theme="barn"),
    "farm_auxiliary": dict(rooms=["barn"], theme="barn"),
    "farm":         dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom"], theme="house"),
    "greenhouse":   dict(rooms=["greenhouse"], theme="shed"),
    "industrial":   dict(rooms=["warehouse", "office", "bathroom"], theme="industrial"),
    "warehouse":    dict(rooms=["warehouse", "office"], theme="industrial"),
    "commercial":   dict(rooms=["generalstore", "storage", "office", "bathroom"], theme="commercial"),
    "retail":       dict(rooms=["generalstore", "storage", "bathroom"], theme="commercial"),
    "office":       dict(rooms=["office", "office", "bathroom", "kitchen"], theme="office"),
    "supermarket":  dict(rooms=["grocery", "grocerystorage", "office", "bathroom"], theme="commercial"),
    "school":       dict(rooms=["classroom", "classroom", "classroom", "hall", "bathroom", "office", "kitchen"], theme="school"),
    "college":      dict(rooms=["classroom", "classroom", "hall", "bathroom", "office", "library"], theme="school"),
    "university":   dict(rooms=["classroom", "classroom", "hall", "bathroom", "office", "library"], theme="school"),
    "hospital":     dict(rooms=["medical", "medical", "hall", "bathroom", "office", "kitchen"], theme="medical"),
    "church":       dict(rooms=["church", "office"], theme="church"),
    "chapel":       dict(rooms=["church"], theme="church"),
    "hotel":        dict(rooms=["hall", "bedroom", "bathroom", "bedroom", "bathroom", "kitchen"], theme="hotel"),
    "public":       dict(rooms=["hall", "office", "bathroom"], theme="office"),
    "civic":        dict(rooms=["hall", "office", "bathroom"], theme="office"),
    "government":   dict(rooms=["hall", "office", "bathroom"], theme="office"),
    "fire_station": dict(rooms=["firestorage", "office", "bathroom", "kitchen"], theme="industrial"),
    "police":       dict(rooms=["policestorage", "office", "hall", "bathroom"], theme="office"),
    "kindergarten": dict(rooms=["classroom", "bathroom", "kitchen"], theme="school"),
    "sports_hall":  dict(rooms=["gym", "lockerroom", "bathroom"], theme="school"),
    "stadium":      dict(rooms=["gym", "lockerroom", "bathroom"], theme="school"),
    "train_station":dict(rooms=["hall", "office"], theme="office"),
    "transportation":dict(rooms=["hall", "office"], theme="office"),
    "service":      dict(rooms=["storage"], theme="shed"),
    "roof":         dict(rooms=["parkingstall"], theme="garage"),
    "carport":      dict(rooms=["parkingstall"], theme="garage"),
    "yes":          dict(rooms=["livingroom", "kitchen", "bedroom", "bathroom"], theme="house"),
}
# amenity / shop tags override the "building" value when present
AMENITY_THEMES = {
    "police": "police", "fire_station": "fire_station", "hospital": "hospital", "clinic": "hospital",
    "doctors": "hospital", "dentist": "hospital", "pharmacy": "pharmacy", "school": "school",
    "college": "college", "university": "university", "kindergarten": "kindergarten",
    "place_of_worship": "church", "restaurant": "restaurant", "fast_food": "restaurant",
    "cafe": "cafe", "bar": "bar", "pub": "bar", "bank": "office", "post_office": "office",
    "library": "library", "townhall": "government", "fuel": "gasstation", "car_repair": "garage_shop",
    "community_centre": "public", "theatre": "public", "cinema": "public", "arena": "sports_hall",
}
SHOP_THEMES = {
    "supermarket": "supermarket", "convenience": "convenience", "hardware": "hardware", "doityourself": "hardware",
    "clothes": "clothing", "department_store": "department", "mall": "department", "car": "cardealer",
    "car_repair": "garage_shop", "gun": "gunstore", "hunting": "gunstore", "sports": "sportstore",
    "books": "bookstore", "pharmacy": "pharmacy", "chemist": "pharmacy", "alcohol": "liquorstore",
    "bakery": "bakery", "butcher": "butcher", "electronics": "electronics", "furniture": "furniturestore",
    "garden_centre": "gardenstore", "pet": "petstore", "variety_store": "generalstore",
}
EXTRA_THEMES = {
    "pharmacy":     dict(rooms=["pharmacy", "pharmacystorage", "bathroom"], theme="commercial"),
    "restaurant":   dict(rooms=["restaurant", "restaurantkitchen", "bathroom"], theme="commercial"),
    "cafe":         dict(rooms=["cafe", "kitchen", "bathroom"], theme="commercial"),
    "bar":          dict(rooms=["bar", "barkitchen", "bathroom"], theme="commercial"),
    "library":      dict(rooms=["library", "office", "bathroom"], theme="office"),
    "gasstation":   dict(rooms=["gasstore", "gasstorage", "bathroom"], theme="commercial"),
    "garage_shop":  dict(rooms=["mechanic", "office", "bathroom"], theme="industrial"),
    "convenience":  dict(rooms=["conveniencestore", "storage", "bathroom"], theme="commercial"),
    "hardware":     dict(rooms=["toolstore", "toolstorage", "bathroom"], theme="commercial"),
    "clothing":     dict(rooms=["clothingstore", "clothingstorage", "bathroom"], theme="commercial"),
    "department":   dict(rooms=["departmentstore", "storage", "clothingstore", "electronicsstore", "bathroom"], theme="commercial"),
    "cardealer":    dict(rooms=["cardealer", "office", "bathroom"], theme="commercial"),
    "gunstore":     dict(rooms=["gunstore", "gunstorestorage"], theme="commercial"),
    "sportstore":   dict(rooms=["sportstore", "sportstorage"], theme="commercial"),
    "bookstore":    dict(rooms=["bookstore", "storage"], theme="commercial"),
    "liquorstore":  dict(rooms=["liquorstore", "storage"], theme="commercial"),
    "bakery":       dict(rooms=["bakery", "bakerykitchen"], theme="commercial"),
    "butcher":      dict(rooms=["butcher", "butcherstorage"], theme="commercial"),
    "electronics":  dict(rooms=["electronicsstore", "storage"], theme="commercial"),
    "furniturestore": dict(rooms=["furniturestore", "storage"], theme="commercial"),
    "gardenstore":  dict(rooms=["gardenstore", "storage"], theme="commercial"),
    "petstore":     dict(rooms=["petstore", "storage"], theme="commercial"),
    "generalstore": dict(rooms=["generalstore", "storage"], theme="commercial"),
}
BUILDING_THEMES.update(EXTRA_THEMES)

# Vehicle zone names (objects.lua, type="Vehicle") keyed by what the OSM feature is.
VEHICLE_ZONES = dict(
    parking="parkingstall", police="police", fire="fire", hospital="medical", fuel="parkingstall",
    farm="farm", junkyard="junkyard", car_dealer="cardealer", school="parkingstall", residential="parkingstall",
)

# Zombie density (0-255 for the GenerateLots spawn map) by zone kind
ZOMBIE_DENSITY = dict(downtown=120, town=70, suburb=40, commercial=90, industrial=50, rural=8, forest=4, highway=20)

# Spawn points: lon/lat of well-known spots. The generator snaps them to the nearest
# generated house so the player always starts indoors.
SPAWN_POINTS = {
    "Moncton (Downtown)":      (46.0878, -64.7782),
    "Moncton (Riverview)":     (46.0620, -64.8050),
    "Dieppe":                  (46.0990, -64.7250),
    "Salisbury":               (46.0400, -65.0450),
    "Petitcodiac":             (45.9400, -65.1700),
    "Havelock":                (45.9850, -65.3500),
    "Shediac":                 (46.2200, -64.5400),
    "Hillsborough":            (45.9240, -64.6480),
    "Alma (Fundy)":            (45.6030, -64.9440),
}

# Points of interest. Coordinates are approximate (from memory, roughly +-150 m); the generator
# snaps each one to the nearest OSM feature carrying a matching name when one exists, which puts
# it exactly on the real building/park. kind -> in-game map icon class.
POIS = [
    # (title, kind, lat, lon, name-needle, optional {"street": ..., "housenumber": ...} for exact address snapping)
    # Moncton
    ("Magnetic Hill", "landmark", 46.1395, -64.8785, "Magnetic Hill", None),
    ("Magnetic Hill Zoo", "landmark", 46.1380, -64.8730, "Magnetic Hill Zoo", None),
    ("Magic Mountain Water Park", "landmark", 46.1370, -64.8700, "Magic Mountain", None),
    ("Casino New Brunswick", "commercial", 46.1360, -64.8690, "Casino", None),
    ("Avenir Centre", "arena", 46.0897, -64.7745, "Avenir Centre", {"street": "Main", "housenumber": "150"}),
    ("Moncton Coliseum", "arena", 46.1105, -64.8300, "Coliseum", None),
    ("Capitol Theatre", "landmark", 46.0890, -64.7795, "Capitol Theatre", {"street": "Main", "housenumber": "811"}),
    ("Resurgo Place (Moncton Museum)", "landmark", 46.0920, -64.7730, "Resurgo", {"street": "Mountain", "housenumber": "20"}),
    ("Bore View Park (Tidal Bore)", "park", 46.0960, -64.7690, "Bore", None),
    ("Victoria Park", "park", 46.0968, -64.7855, "Victoria Park", None),
    ("Centennial Park", "park", 46.0980, -64.8160, "Centennial Park", None),
    ("Mapleton Park", "park", 46.1180, -64.8440, "Mapleton Park", None),
    ("Irishtown Nature Park", "park", 46.1480, -64.7640, "Irishtown", None),
    ("Jones Lake", "water", 46.0945, -64.7920, "Jones Lake", None),
    ("The Moncton Hospital", "hospital", 46.1017, -64.7960, "Moncton Hospital", {"street": "Macbeath", "housenumber": "135"}),
    ("Dr. Georges-L.-Dumont University Hospital Centre", "hospital", 46.1035, -64.7620, "Dumont", {"street": "Dr. Georges-L.-Dumont", "housenumber": "330"}),
    ("Universite de Moncton", "school", 46.1040, -64.7780, "Universit", None),
    ("Crandall University", "school", 46.1230, -64.8290, "Crandall", None),
    ("Codiac Regional RCMP (new detachment, 199 Albert St)", "police", 46.0930, -64.7720, "RCMP", {"street": "Albert", "housenumber": "199"}),
    ("Codiac Regional RCMP (former HQ, 520 Main St)", "police", 46.0905, -64.7765, "RCMP", {"street": "Main", "housenumber": "520"}),
    ("Moncton Fire Station 1 (80 Caledonia Rd)", "fire", 46.1075, -64.8250, "Fire", {"street": "Caledonia", "housenumber": "80"}),
    ("Moncton Fire Station 2 (800 St. George Blvd)", "fire", 46.0940, -64.8150, "Fire", {"street": "St. George", "housenumber": "800"}),
    ("Moncton Fire Station 3 (299 Botsford St)", "fire", 46.0960, -64.7760, "Fire", {"street": "Botsford", "housenumber": "299"}),
    ("Moncton Fire Station (72 Brandon St)", "fire", 46.1020, -64.7560, "Fire", {"street": "Brandon", "housenumber": "72"}),
    ("Moncton Fire Station 5 (99 Hildegarde Dr)", "fire", 46.1280, -64.7990, "Fire", {"street": "Hildegard", "housenumber": "99"}),
    ("Greater Moncton Romeo LeBlanc International Airport", "airport", 46.1122, -64.6786, "Airport", None),
    ("CF Champlain (Champlain Place)", "commercial", 46.0975, -64.7268, "Champlain", {"street": "Paul", "housenumber": "477"}),
    ("Costco Moncton", "commercial", 46.1080, -64.8310, "Costco", None),
    ("Trinity Drive retail", "commercial", 46.1200, -64.8360, "Trinity", None),
    ("Moncton Market", "commercial", 46.0905, -64.7775, "Moncton Market", {"street": "Westmorland", "housenumber": "120"}),
    ("Riverview Mill Creek Nature Park", "park", 46.0470, -64.8380, "Mill Creek", None),
    ("Gunningsville Bridge", "landmark", 46.0885, -64.7890, "Gunningsville", None),
    ("Dieppe Market", "commercial", 46.0985, -64.7225, "Dieppe Market", None),
    ("CN Gordon Yard", "industrial", 46.1250, -64.7250, "Gordon Yard", None),
    # Shediac
    ("The World's Largest Lobster (Rotary Park)", "landmark", 46.2185, -64.5495, "Lobster", None),
    ("Parlee Beach Provincial Park", "beach", 46.2410, -64.5110, "Parlee", None),
    ("Pointe-du-Chene Wharf", "landmark", 46.2375, -64.5080, "Pointe-du-Ch", None),
    ("Shediac Island", "landmark", 46.2300, -64.5300, "Shediac Island", None),
    ("Shediac RCMP Detachment (77 Ohio Rd)", "police", 46.2215, -64.5415, "RCMP", {"street": "Ohio", "housenumber": "77"}),
    ("Shediac Bay Marina", "landmark", 46.2240, -64.5330, "Marina", None),
    # Route 114 / Fundy coast
    ("Hillsborough (Albert County Museum)", "landmark", 45.9240, -64.6480, "Museum", None),
    ("Hopewell Rocks (the Flowerpot Rocks)", "landmark", 45.8210, -64.5790, "Hopewell Rocks", None),
    ("Hopewell Cape", "town", 45.8560, -64.5730, "Hopewell Cape", None),
    ("Riverside-Albert", "town", 45.7470, -64.7450, "Riverside-Albert", None),
    ("Cape Enrage Lighthouse", "landmark", 45.5955, -64.7790, "Cape Enrage", None),
    ("Alma", "town", 45.6030, -64.9440, "Alma", None),
    ("Fundy National Park Headquarters", "landmark", 45.5990, -64.9500, "Fundy National Park", None),
    ("Herring Cove", "beach", 45.5880, -64.9290, "Herring Cove", None),
    ("Dickson Falls", "landmark", 45.5990, -64.9680, "Dickson Falls", None),
    # West
    ("Salisbury Big Stop", "commercial", 46.0400, -65.0400, "Big Stop", None),
    ("Petitcodiac", "town", 45.9400, -65.1700, "Petitcodiac", None),
    ("Havelock", "town", 45.9850, -65.3500, "Havelock", None),
]
