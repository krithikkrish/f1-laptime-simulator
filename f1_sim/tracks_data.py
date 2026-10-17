"""
Official real-world GPS Cartesian track coordinates (in meters) and environmental
data for all 24 Grand Prix circuits on the FIA Formula 1 World Championship calendar.
Derived from authentic OpenF1 sessions, FIA timing sectors, and GPS spline geometry.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

from .track import Track, build_track_from_waypoints
from .physics_weather import WeatherConditions

# Path to the bundled master JSON containing authentic 3D waypoints for all 24 circuits
ALL_TRACKS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "all_tracks.json")

_TRACKS_CACHE: Optional[Dict[str, Any]] = None


def get_all_tracks_data() -> Dict[str, Any]:
    """Loads and caches the 24-circuit master dataset."""
    global _TRACKS_CACHE
    if _TRACKS_CACHE is None:
        if os.path.exists(ALL_TRACKS_JSON):
            with open(ALL_TRACKS_JSON, "r", encoding="utf-8") as f:
                _TRACKS_CACHE = json.load(f)
        else:
            _TRACKS_CACHE = {}
    return _TRACKS_CACHE


# Common aliases mapping country/colloquial names to canonical keys
CIRCUIT_ALIASES = {
    "monza": "monza",
    "italy": "monza",
    "silverstone": "silverstone",
    "great britain": "silverstone",
    "britain": "silverstone",
    "british": "silverstone",
    "uk": "silverstone",
    "spa": "spa-francorchamps",
    "belgium": "spa-francorchamps",
    "spa-francorchamps": "spa-francorchamps",
    "monaco": "monte_carlo",
    "monte carlo": "monte_carlo",
    "monte_carlo": "monte_carlo",
    "bahrain": "sakhir",
    "sakhir": "sakhir",
    "jeddah": "jeddah",
    "saudi": "jeddah",
    "saudi arabia": "jeddah",
    "melbourne": "melbourne",
    "australia": "melbourne",
    "albert park": "melbourne",
    "suzuka": "suzuka",
    "japan": "suzuka",
    "shanghai": "shanghai",
    "china": "shanghai",
    "miami": "miami",
    "imola": "imola",
    "emilia romagna": "imola",
    "montreal": "montreal",
    "canada": "montreal",
    "gilles villeneuve": "montreal",
    "catalunya": "catalunya",
    "barcelona": "catalunya",
    "spain": "catalunya",
    "spielberg": "spielberg",
    "austria": "spielberg",
    "red bull ring": "spielberg",
    "hungaroring": "hungaroring",
    "hungary": "hungaroring",
    "budapest": "hungaroring",
    "zandvoort": "zandvoort",
    "netherlands": "zandvoort",
    "dutch": "zandvoort",
    "baku": "baku",
    "azerbaijan": "baku",
    "singapore": "singapore",
    "marina bay": "singapore",
    "austin": "austin",
    "cota": "austin",
    "united states": "austin",
    "usa": "austin",
    "mexico": "mexico_city",
    "mexico city": "mexico_city",
    "mexico_city": "mexico_city",
    "interlagos": "interlagos",
    "brazil": "interlagos",
    "sao paulo": "interlagos",
    "las vegas": "las_vegas",
    "las_vegas": "las_vegas",
    "vegas": "las_vegas",
    "lusail": "lusail",
    "qatar": "lusail",
    "yas marina": "yas_marina_circuit",
    "yas_marina": "yas_marina_circuit",
    "yas_marina_circuit": "yas_marina_circuit",
    "abu dhabi": "yas_marina_circuit",
    "uae": "yas_marina_circuit"
}


def find_canonical_circuit_key(name_or_key: Union[str, int]) -> str:
    """Fuzzy-matches any user-provided name, key, or country to a canonical circuit key."""
    if isinstance(name_or_key, int):
        all_data = get_all_tracks_data()
        for k, v in all_data.items():
            if v.get("meeting_key") == name_or_key:
                return k

    query = str(name_or_key).strip().lower()
    if query in CIRCUIT_ALIASES:
        return CIRCUIT_ALIASES[query]

    # Search in all_tracks dictionary
    all_data = get_all_tracks_data()
    if query in all_data:
        return query

    # Substring search
    for alias, canon in CIRCUIT_ALIASES.items():
        if alias in query or query in alias:
            return canon

    for k, v in all_data.items():
        if (query in k or 
            query in v.get("short_name", "").lower() or 
            query in v.get("country", "").lower() or 
            query in v.get("official_name", "").lower()):
            return k

    return "monza"


def get_available_circuits_list() -> List[Dict[str, Any]]:
    """Returns a list of all 24 Grand Prix circuits with display labels and metadata."""
    all_data = get_all_tracks_data()
    circuits = []
    for k, v in all_data.items():
        circuits.append({
            "key": k,
            "meeting_key": v.get("meeting_key"),
            "short_name": v.get("short_name"),
            "country": v.get("country"),
            "official_name": v.get("official_name"),
            "length_m": v.get("length_m"),
            "pole_driver": v.get("pole_driver"),
            "pole_lap_time": v.get("pole_lap_time"),
            "label": f"{v.get('country')} — {v.get('short_name')} ({v.get('length_m'):,.0f} m)"
        })
    return circuits


def create_calendar_track(
    circuit_identifier: Union[str, int],
    ds: float = 1.0
) -> Tuple[Track, WeatherConditions, Dict[str, Any]]:
    """
    Creates an authentic Track object and genuine WeatherConditions
    for any chosen circuit on the 24-race FIA Formula 1 calendar.
    """
    canon_key = find_canonical_circuit_key(circuit_identifier)
    all_data = get_all_tracks_data()
    
    if canon_key not in all_data:
        # Emergency fallback to Monza
        canon_key = "monza"
        
    data = all_data[canon_key]
    
    x = np.array(data["x"], dtype=float)
    y = np.array(data["y"], dtype=float)
    z = np.array(data.get("z", [0.0] * len(x)), dtype=float)
    
    track_name = data.get("official_name", f"{data.get('short_name', 'Grand Prix')} Circuit")
    track = build_track_from_waypoints(track_name, x, y, z, ds=ds)
    
    # Timing sectors
    raw_sectors = data.get("sectors", [])
    if raw_sectors:
        track.sectors = [(sec[0], float(sec[1]), float(sec[2])) for sec in raw_sectors]
    else:
        track.sectors = [
            ("Sector 1", 0.0, track.length * 0.33),
            ("Sector 2", track.length * 0.33, track.length * 0.67),
            ("Sector 3", track.length * 0.67, track.length)
        ]
        
    weather = WeatherConditions(
        air_temp_c=float(data.get("air_temp_c", 25.0)),
        track_temp_c=float(data.get("track_temp_c", 38.0)),
        humidity_pct=float(data.get("humidity_pct", 50.0)),
        pressure_hpa=float(data.get("pressure_hpa", 1013.25)),
        wind_speed_ms=float(data.get("wind_speed_ms", 2.0)),
        wind_dir_deg=float(data.get("wind_dir_deg", 180.0)),
        rainfall=0
    )
    
    meta = {
        "meeting_key": data.get("meeting_key"),
        "country": data.get("country"),
        "pole_driver": data.get("pole_driver"),
        "pole_team": data.get("pole_team"),
        "pole_lap_time": data.get("pole_lap_time")
    }
    
    return track, weather, meta


# Backwards compatibility creators
def create_monza_track(ds: float = 1.0) -> Track:
    track, _, _ = create_calendar_track("monza", ds=ds)
    return track

def create_silverstone_track(ds: float = 1.0) -> Track:
    track, _, _ = create_calendar_track("silverstone", ds=ds)
    return track

def create_spa_track(ds: float = 1.0) -> Track:
    track, _, _ = create_calendar_track("spa-francorchamps", ds=ds)
    return track

def create_monaco_track(ds: float = 1.0) -> Track:
    track, _, _ = create_calendar_track("monte_carlo", ds=ds)
    return track

def create_bahrain_track(ds: float = 1.0) -> Track:
    track, _, _ = create_calendar_track("sakhir", ds=ds)
    return track

def create_suzuka_track(ds: float = 1.0) -> Track:
    track, _, _ = create_calendar_track("suzuka", ds=ds)
    return track


# Compatibility variables for legacy tests
all_data = get_all_tracks_data()
if "monza" in all_data:
    MONZA_X = all_data["monza"]["x"]
    MONZA_Y = all_data["monza"]["y"]
else:
    MONZA_X = [0.0, 100.0, 200.0]
    MONZA_Y = [0.0, 200.0, 0.0]

if "silverstone" in all_data:
    SILVERSTONE_X = all_data["silverstone"]["x"]
    SILVERSTONE_Y = all_data["silverstone"]["y"]
else:
    SILVERSTONE_X = [0.0, 100.0, 200.0]
    SILVERSTONE_Y = [0.0, 200.0, 0.0]
