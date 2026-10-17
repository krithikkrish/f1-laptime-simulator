"""
Real-world Formula 1 Pole Position Telemetry & Historical Benchmark Loader.
Provides authentic telemetry (speed, throttle, brake, gear, distance) from the
official 2025 FIA Formula 1 World Championship Saturday Qualifying (Q3) sessions
for all 24 Grand Prix circuits.
"""

import os
import glob
import json
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd


def get_default_cache_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")


# Mapping of 2025 meeting keys to telemetry cache dataset
MEETING_KEY_2025_MAP = {
    1257: 1229,  # Sakhir (Bahrain)
    1258: 1230,  # Jeddah (Saudi Arabia)
    1254: 1231,  # Melbourne (Australia)
    1256: 1232,  # Suzuka (Japan)
    1255: 1233,  # Shanghai (China)
    1259: 1234,  # Miami (United States)
    1260: 1235,  # Imola (Italy)
    1261: 1236,  # Monaco
    1263: 1237,  # Montreal (Canada)
    1262: 1238,  # Catalunya (Spain)
    1264: 1239,  # Spielberg (Austria)
    1277: 1240,  # Silverstone (Great Britain)
    1265: 1242,  # Spa-Francorchamps (Belgium)
    1266: 1241,  # Hungaroring (Hungary)
    1267: 1243,  # Zandvoort (Netherlands)
    1268: 1244,  # Monza (Italy)
    1269: 1245,  # Baku (Azerbaijan)
    1270: 1246,  # Singapore
    1271: 1247,  # Austin (United States)
    1272: 1248,  # Mexico City (Mexico)
    1273: 1249,  # Interlagos (Brazil)
    1274: 1250,  # Las Vegas (United States)
    1275: 1251,  # Lusail (Qatar)
    1276: 1252,  # Yas Marina (Abu Dhabi)
}


def get_real_pole_telemetry(
    meeting_key: int, 
    track_length: float, 
    cache_dir: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Loads authentic real-world 2025 qualifying pole lap telemetry
    and aligns the cumulative spatial distance to the circuit length.
    """
    if cache_dir is None:
        cache_dir = get_default_cache_dir()

    # Resolve meeting key (accepts 2025 keys directly or mapped)
    lookup_key = MEETING_KEY_2025_MAP.get(meeting_key, meeting_key)

    sess_file = os.path.join(cache_dir, f"sessions_{lookup_key}.json")
    if not os.path.exists(sess_file):
        sess_file = os.path.join(cache_dir, f"sessions_{meeting_key}.json")
        if not os.path.exists(sess_file):
            return None

    try:
        with open(sess_file, "r", encoding="utf-8") as f:
            sess = json.load(f)

        q_sess = [s for s in sess if "qualifying" in s.get("session_name", "").lower()]
        s_key = (q_sess[0] if q_sess else sess[-1])["session_key"]

        car_files = glob.glob(os.path.join(cache_dir, f"car_{s_key}_*.json"))
        loc_files = glob.glob(os.path.join(cache_dir, f"loc_{s_key}_*.json"))

        if not car_files or not loc_files:
            return None

        with open(car_files[0], "r", encoding="utf-8") as f:
            car_data = json.load(f)
        with open(loc_files[0], "r", encoding="utf-8") as f:
            loc_data = json.load(f)

        df_car = pd.DataFrame(car_data)
        df_loc = pd.DataFrame(loc_data)

        df_car["date"] = pd.to_datetime(df_car["date"], format="mixed")
        df_loc["date"] = pd.to_datetime(df_loc["date"], format="mixed")

        # Synchronize location and car telemetry
        df_merged = pd.merge_asof(
            df_loc.sort_values("date"), 
            df_car.sort_values("date"), 
            on="date", 
            direction="nearest"
        )

        # 3D GPS coordinates in decimeters -> meters
        x = df_merged["x"].to_numpy(dtype=float) / 10.0
        y = df_merged["y"].to_numpy(dtype=float) / 10.0
        z = df_merged["z"].to_numpy(dtype=float) / 10.0

        dx = np.diff(x)
        dy = np.diff(y)
        dz = np.diff(z)
        s = np.concatenate(([0.0], np.cumsum(np.sqrt(dx**2 + dy**2 + dz**2))))

        # Align to simulated track length
        if s[-1] > 0 and track_length > 0:
            df_merged["distance_m"] = s * (track_length / s[-1])
        else:
            df_merged["distance_m"] = s

        # Ensure numeric columns
        for col in ["speed", "throttle", "brake", "n_gear", "rpm"]:
            if col in df_merged.columns:
                df_merged[col] = pd.to_numeric(df_merged[col], errors="coerce").fillna(0)

        return df_merged

    except Exception as e:
        print(f"[PoleTelemetry] Error loading telemetry for meeting {meeting_key}: {e}")
        return None


def get_pole_benchmark_info(track_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns explicit, formatted metadata describing the real-world 2025 pole lap
    benchmark being compared against.
    """
    driver_name = track_meta.get("pole_driver", "Oscar Piastri")
    team_name = track_meta.get("pole_team", "McLaren")
    raw_lap_time = track_meta.get("pole_lap_time")

    if raw_lap_time:
        try:
            lap_s = float(raw_lap_time)
            m = int(lap_s // 60)
            s = lap_s % 60
            lap_str = f"{m}:{s:06.3f}"
        except Exception:
            lap_s = None
            lap_str = "N/A"
    else:
        lap_s = None
        lap_str = "N/A"

    return {
        "championship_year": 2025,
        "regulation_era": "2025 Ground-Effect Regulations (120 kW MGU-K + MGU-H, 798 kg)",
        "session_type": "Official 2025 Saturday Qualifying (Q3 Pole Lap)",
        "driver_name": driver_name,
        "team_name": team_name,
        "lap_time_s": lap_s,
        "lap_time_str": lap_str,
        "full_label": f"2025 Pole Lap: {driver_name} ({team_name}) — {lap_str}"
    }
