"""
Live & Historical Formula 1 Data Client via OpenF1 API (api.openf1.org).
Provides real-world sessions, weather stations, car telemetry, and 3D GPS locations
for every Grand Prix circuit on the FIA Formula 1 World Championship calendar.
"""

import os
import json
import ssl
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

from .physics_weather import WeatherConditions
from .track import build_track_from_waypoints, Track


class OpenF1Client:
    BASE_URL = "https://api.openf1.org/v1"

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.ssl_ctx = ssl._create_unverified_context()

    def _get(self, endpoint: str, params: Dict[str, Any], cache_filename: Optional[str] = None) -> List[Dict[str, Any]]:
        """Makes cached HTTP GET request to OpenF1 API."""
        if cache_filename:
            cache_path = os.path.join(self.cache_dir, cache_filename)
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass

        query_str = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}/{endpoint}?{query_str}"
        req = urllib.request.Request(url, headers={"User-Agent": "F1-LTS-Simulator/2026"})

        import time
        max_retries = 4
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if cache_filename and data:
                        cache_path = os.path.join(self.cache_dir, cache_filename)
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                    return data
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < max_retries - 1:
                    wait_s = 2.0 * (attempt + 1)
                    time.sleep(wait_s)
                    continue
                print(f"[OpenF1] Warning: Failed request {url}: {e}")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                    continue
                print(f"[OpenF1] Warning: Failed request {url}: {e}")
                break

        if cache_filename:
            cache_path = os.path.join(self.cache_dir, cache_filename)
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        return []


    def get_meetings(self, year: int = 2025) -> List[Dict[str, Any]]:
        """Retrieves all 24 Grand Prix meetings on the calendar for a given championship year."""
        meetings = self._get("meetings", {"year": year}, f"meetings_{year}.json")
        gp_meetings = [m for m in meetings if "testing" not in m.get("meeting_name", "").lower() 
                       and "testing" not in m.get("meeting_official_name", "").lower()]
        return gp_meetings

    def get_sessions_for_meeting(self, meeting_key: int) -> List[Dict[str, Any]]:
        """Retrieves all track sessions (Qualifying, Race, FP) for a meeting."""
        return self._get("sessions", {"meeting_key": meeting_key}, f"sessions_{meeting_key}.json")

    def get_weather(self, session_key: int) -> WeatherConditions:
        """Retrieves session weather telemetry and returns a typed WeatherConditions object."""
        data = self._get("weather", {"session_key": session_key}, f"weather_{session_key}.json")
        if not data:
            return WeatherConditions()
        
        df = pd.DataFrame(data)
        return WeatherConditions(
            air_temp_c=float(df["air_temperature"].mean()),
            track_temp_c=float(df["track_temperature"].mean()),
            humidity_pct=float(df["humidity"].mean()),
            pressure_hpa=float(df["pressure"].mean()),
            wind_speed_ms=float(df["wind_speed"].mean()),
            wind_dir_deg=float(df["wind_direction"].mean()),
            rainfall=int(df["rainfall"].max())
        )

    def get_fastest_lap(self, session_key: int) -> Optional[Dict[str, Any]]:
        """Finds the fastest pole lap across all drivers in the session."""
        laps = self._get("laps", {"session_key": session_key}, f"laps_{session_key}.json")
        valid_laps = [l for l in laps if l.get("lap_duration") is not None and l.get("lap_duration") > 50.0]
        if not valid_laps:
            return None
        fastest = min(valid_laps, key=lambda x: x["lap_duration"])
        return fastest

    def get_driver_info(self, session_key: int, driver_number: int) -> Dict[str, Any]:
        """Retrieves driver abbreviation, full name, and team."""
        drivers = self._get("drivers", {"session_key": session_key, "driver_number": driver_number}, 
                            f"driver_{session_key}_{driver_number}.json")
        if drivers:
            return drivers[0]
        return {"name_acronym": f"#{driver_number}", "full_name": f"Driver #{driver_number}", "team_name": "F1 Team"}

    def get_complete_lap_data(self, meeting_key: int, year: int = 2025) -> Tuple[Track, WeatherConditions, pd.DataFrame, Dict[str, Any]]:
        """
        Loads the complete, authentic real-world dataset for any chosen Grand Prix:
        1. Identifies the Qualifying session and pole position lap.
        2. Retrieves genuine weather conditions (air/track temp, humidity, pressure, wind).
        3. Retrieves synchronized high-speed telemetry (speed, throttle, brake, gear, DRS).
        4. Reconstructs the 3D GPS track coordinates (X, Y, Z) and returns an authentic Track object.
        """
        sessions = self.get_sessions_for_meeting(meeting_key)
        q_sessions = [s for s in sessions if "qualifying" in s.get("session_name", "").lower()]
        sess = q_sessions[0] if q_sessions else sessions[-1]
        session_key = sess["session_key"]

        weather = self.get_weather(session_key)
        fastest_lap = self.get_fastest_lap(session_key)

        if fastest_lap is None:
            raise RuntimeError(f"No valid lap times found for meeting {meeting_key}")

        driver_num = fastest_lap["driver_number"]
        driver_info = self.get_driver_info(session_key, driver_num)
        fastest_lap["driver_name"] = driver_info.get("full_name", f"Driver #{driver_num}")
        fastest_lap["team_name"] = driver_info.get("team_name", "F1")
        fastest_lap["name_acronym"] = driver_info.get("name_acronym", f"#{driver_num}")

        # Clean timestamps for telemetry & location queries
        t_raw = fastest_lap["date_start"]
        t_start = t_raw.split(".")[0]
        lap_dur = float(fastest_lap["lap_duration"])
        t_end_dt = pd.to_datetime(t_start) + pd.Timedelta(seconds=int(lap_dur) + 3)
        t_end = t_end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # Fetch telemetry and location
        car_params = {"session_key": session_key, "driver_number": driver_num, "date>": t_start, "date<": t_end}
        loc_params = {"session_key": session_key, "driver_number": driver_num, "date>": t_start, "date<": t_end}

        cache_car = f"car_{session_key}_{driver_num}_{t_start.replace(':', '_')}.json"
        cache_loc = f"loc_{session_key}_{driver_num}_{t_start.replace(':', '_')}.json"

        cars = self._get("car_data", car_params, cache_car)
        locs = self._get("location", loc_params, cache_loc)

        if not cars or not locs:
            raise RuntimeError(f"Missing telemetry or location data for session {session_key}")

        df_car = pd.DataFrame(cars)
        df_loc = pd.DataFrame(locs)
        df_car["date"] = pd.to_datetime(df_car["date"], format="mixed")
        df_loc["date"] = pd.to_datetime(df_loc["date"], format="mixed")


        df_merged = pd.merge_asof(df_loc.sort_values("date"), df_car.sort_values("date"), on="date", direction="nearest")

        # OpenF1 locations are in decimeters (1/10 meter)
        x_raw = df_merged["x"].to_numpy(dtype=float) / 10.0
        y_raw = df_merged["y"].to_numpy(dtype=float) / 10.0
        z_raw = df_merged["z"].to_numpy(dtype=float) / 10.0

        # Compute cumulative distance
        dx = np.diff(x_raw)
        dy = np.diff(y_raw)
        dz = np.diff(z_raw)
        s_raw = np.concatenate(([0.0], np.cumsum(np.sqrt(dx**2 + dy**2 + dz**2))))
        df_merged["distance_m"] = s_raw

        # Construct Track object
        circuit_name = sess.get("circuit_short_name", "Grand Prix Circuit")
        country = sess.get("country_name", "")
        track_title = f"{circuit_name} Grand Prix Circuit ({country})"

        track = build_track_from_waypoints(track_title, x_raw, y_raw, z_raw, ds=1.0)

        # Set official timing sectors from real lap sector durations
        s1_dur = float(fastest_lap.get("duration_sector_1") or (lap_dur * 0.33))
        s2_dur = float(fastest_lap.get("duration_sector_2") or (lap_dur * 0.34))
        
        # Estimate spatial boundaries of sectors using reference telemetry
        t_elapsed = (df_merged["date"] - df_merged["date"].iloc[0]).dt.total_seconds().to_numpy()
        idx_s1 = int(np.clip(np.searchsorted(t_elapsed, s1_dur), 0, len(s_raw) - 1))
        idx_s2 = int(np.clip(np.searchsorted(t_elapsed, s1_dur + s2_dur), 0, len(s_raw) - 1))

        s1_m = float(s_raw[idx_s1])
        s2_m = float(s_raw[idx_s2])

        track.sectors = [
            ("Sector 1", 0.0, s1_m),
            ("Sector 2", s1_m, s2_m),
            ("Sector 3", s2_m, track.length)
        ]

        return track, weather, df_merged, fastest_lap
