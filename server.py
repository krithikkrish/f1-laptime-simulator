"""
High-Performance REST API Server for the F1 2026 Lap-Time Simulator.
Connects the transient vehicle dynamics ODE simulation engine and authentic 2024
qualifying pole telemetry directly to the modern React / Vite web frontend.
"""

import os
import sys
import json
import time
import mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import numpy as np
import pandas as pd

from f1_sim.params import VehicleParams
from f1_sim.track import Track
from f1_sim.physics_weather import WeatherConditions
from f1_sim.lts_engine import SimulationEngine, LapTelemetry
from f1_sim.setup_sheet import SETUP_PRESETS
from f1_sim.tracks_data import create_calendar_track, get_available_circuits_list
from f1_sim.pole_telemetry import get_real_pole_telemetry, get_pole_benchmark_info
from f1_sim.motec_export import export_to_motec_csv, export_to_motec_ldx_beacon

COUNTRY_FLAGS = {
    "Bahrain": "🇧🇭", "Saudi Arabia": "🇸🇦", "Australia": "🇦🇺", "Japan": "🇯🇵",
    "China": "🇨🇳", "United States": "🇺🇸", "USA": "🇺🇸", "Italy": "🇮🇹",
    "Monaco": "🇲🇨", "Canada": "🇨🇦", "Spain": "🇪🇸", "Austria": "🇦🇹",
    "Great Britain": "🇬🇧", "United Kingdom": "🇬🇧", "Hungary": "🇭🇺", "Belgium": "🇧🇪", "Netherlands": "🇳🇱",
    "Azerbaijan": "🇦🇿", "Singapore": "🇸🇬", "Mexico": "🇲🇽", "Brazil": "🇧🇷",
    "Qatar": "🇶🇦", "United Arab Emirates": "🇦🇪", "UAE": "🇦🇪"
}

def format_lap_str(seconds: float) -> str:
    if seconds is None or np.isnan(seconds) or seconds <= 0:
        return "N/A"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:06.3f}" if m > 0 else f"{s:.3f} s"


class F1SimulationHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local Vite dev server
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/tracks":
            self.handle_get_tracks()
        elif path == "/api/health":
            self.send_json({"status": "ok", "time": time.time()})
        else:
            self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/simulate":
            self.handle_simulate()
        else:
            self.send_error(404, "Endpoint not found")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_get_tracks(self):
        raw_circuits = get_available_circuits_list()
        tracks = []
        for c in raw_circuits:
            flag = COUNTRY_FLAGS.get(c.get("country", ""), "🏁")
            pole_time_raw = c.get("pole_lap_time")
            pole_str = format_lap_str(float(pole_time_raw)) if pole_time_raw else "N/A"
            tracks.append({
                "key": c["key"],
                "meeting_key": c.get("meeting_key"),
                "short_name": c.get("short_name"),
                "country": c.get("country"),
                "flag": flag,
                "official_name": c.get("official_name"),
                "length_m": c.get("length_m"),
                "pole_driver": c.get("pole_driver", "Pole Sitter"),
                "pole_lap_time": pole_time_raw,
                "pole_lap_str": pole_str,
                "benchmark_label": f"2024 Pole: {c.get('pole_driver', 'Pole Sitter')} ({pole_str})"
            })
        self.send_json({"tracks": tracks})

    def handle_simulate(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body) if body else {}

            track_key = payload.get("track_key", "miami")
            compound = payload.get("compound", "Soft Slick")
            fuel_kg = float(payload.get("fuel_kg", 25.0))
            setup_mode = payload.get("setup", "balanced")

            # 1. Load Track and Authentic Pole Telemetry
            track, active_weather, track_meta = create_calendar_track(track_key, ds=1.0)
            pole_info = get_pole_benchmark_info(track_meta)
            ref_df = get_real_pole_telemetry(track_meta.get("meeting_key"), track.length)

            # 2. Configure Setup Preset
            if setup_mode in ("high_speed", "monza", "Monza Low-Drag Spec"):
                preset = SETUP_PRESETS["Monza Low-Drag Spec"]
            elif setup_mode in ("high_downforce", "monaco", "High-Downforce Monaco Spec"):
                preset = SETUP_PRESETS["High-Downforce Monaco Spec"]
            elif "Wet" in compound or setup_mode in ("wet", "Wet-Weather Spec"):
                preset = SETUP_PRESETS["Wet-Weather Spec"]
            else:
                preset = SETUP_PRESETS["Balanced Grand Prix Spec"]

            # Overrides if provided
            ice_kw = float(payload.get("ice_kw", preset.ice_power_kw))
            mguk_kw = float(payload.get("mguk_kw", preset.mguk_power_kw))
            v_taper = float(payload.get("v_taper", preset.mguk_taper_start_kmh))
            v_cutoff = float(payload.get("v_cutoff", preset.mguk_taper_end_kmh))
            cl_z = float(payload.get("cl_z", preset.cl_a_z_mode))
            cd_x = float(payload.get("cd_x", preset.cd_a_x_mode))
            bbw_bias = float(payload.get("bbw_bias", preset.brake_bias_front_pct))
            soc_init = float(payload.get("soc_init", 1.0))

            # 3. Tire Physics
            if "Soft" in compound:
                mu_val = 1.76
                is_wet = False
            elif "Medium" in compound:
                mu_val = 1.70
                is_wet = False
            elif "Hard" in compound:
                mu_val = 1.62
                is_wet = False
            else:
                mu_val = 1.25
                is_wet = True

            # 4. Run Physics ODE Engine
            params = VehicleParams(
                mass_empty=preset.car_empty_mass_kg,
                fuel_mass=fuel_kg,
                p_ice_max=ice_kw * 1e3,
                p_mguk_deploy_max=mguk_kw * 1e3,
                p_mguk_regen_max=mguk_kw * 1e3,
                v_taper_start_kmh=v_taper,
                v_taper_end_kmh=v_cutoff,
                cl_A_z_mode=cl_z,
                cd_A_z_mode=preset.cd_a_z_mode,
                cl_A_x_mode=preset.cl_a_x_mode,
                cd_A_x_mode=cd_x,
                mu_peak=mu_val,
                tire_compound="WET" if is_wet else "SLICK"
            )

            engine = SimulationEngine(params=params, weather=active_weather)
            engine.dual_track.aero_balance_f = preset.aero_balance_front_pct / 100.0
            engine.dual_track.bbw_base_front_pct = bbw_bias / 100.0

            t0 = time.perf_counter()
            sim_telem: LapTelemetry = engine.run_transient_simulation(
                track=track,
                initial_soc=soc_init,
                weather=active_weather
            )
            calc_time_ms = (time.perf_counter() - t0) * 1000.0

            # 5. Delta vs Authentic 2024 Saturday Q3 Pole Lap
            ref_time = pole_info.get("lap_time_s")
            delta_s = (sim_telem.lap_time - ref_time) if ref_time else None
            sim_lap_str = format_lap_str(sim_telem.lap_time)
            ref_lap_str = pole_info.get("lap_time_str", "N/A")

            # 6. Downsample Telemetry to ~250 points for 60fps Web Rendering
            n_pts = 250
            s_target = np.linspace(0, track.length, n_pts)

            speed_2026 = np.interp(s_target, sim_telem.s, sim_telem.v_kmh)
            throttle = np.interp(s_target, sim_telem.s, sim_telem.throttle * 100.0)
            brake = np.interp(s_target, sim_telem.s, sim_telem.brake * 100.0)
            gear = np.round(np.interp(s_target, sim_telem.s, sim_telem.gear if sim_telem.gear is not None else np.zeros_like(sim_telem.s))).astype(int)
            rpm = np.interp(s_target, sim_telem.s, getattr(sim_telem, "engine_rpm", np.zeros_like(sim_telem.s)))
            p_ice = np.interp(s_target, sim_telem.s, sim_telem.p_ice_kw)
            p_mguk = np.interp(s_target, sim_telem.s, sim_telem.p_mguk_kw)
            soc = np.interp(s_target, sim_telem.s, sim_telem.soc_percent)
            t_tire = np.interp(s_target, sim_telem.s, sim_telem.t_tire_c)

            # Loads converted to kilograms
            f_fl = getattr(sim_telem, "f_z_fl", np.zeros_like(sim_telem.s))
            f_fr = getattr(sim_telem, "f_z_fr", np.zeros_like(sim_telem.s))
            f_rl = getattr(sim_telem, "f_z_rl", np.zeros_like(sim_telem.s))
            f_rr = getattr(sim_telem, "f_z_rr", np.zeros_like(sim_telem.s))
            front_load_kg = np.interp(s_target, sim_telem.s, (f_fl + f_fr) / 9.81)
            rear_load_kg = np.interp(s_target, sim_telem.s, (f_rl + f_rr) / 9.81)
            downforce_kg = np.interp(s_target, sim_telem.s, sim_telem.f_downforce_n / 9.81)

            # Authentic 2024 Pole Lap Speed Profile
            if ref_df is not None and "distance_m" in ref_df.columns and "speed" in ref_df.columns:
                speed_2024 = np.interp(s_target, ref_df["distance_m"], ref_df["speed"])
                ref_top_kmh = float(ref_df["speed"].max())
            else:
                speed_2024 = None
                ref_top_kmh = None

            # Subsampled Track Waypoints for 2D Canvas / SVG Map
            track_step = max(1, len(track.x) // 180)
            map_pts = [{"x": round(float(x), 1), "y": round(float(y), 1)} for x, y in zip(track.x[::track_step], track.y[::track_step])]

            response_data = {
                "track": {
                    "key": track_key,
                    "name": track.name,
                    "length_m": float(track.length),
                    "flag": COUNTRY_FLAGS.get(track_meta.get("country", ""), "🏁"),
                    "country": track_meta.get("country", "")
                },
                "pole_benchmark": {
                    "year": 2024,
                    "session": "Official Saturday Qualifying (Q3)",
                    "driver_name": pole_info["driver_name"],
                    "team_name": pole_info["team_name"],
                    "lap_time_str": ref_lap_str,
                    "lap_time_s": ref_time,
                    "top_speed_kmh": ref_top_kmh
                },
                "results": {
                    "lap_time_s": float(sim_telem.lap_time),
                    "lap_time_str": sim_lap_str,
                    "delta_s": float(delta_s) if delta_s is not None else None,
                    "faster_than_pole": bool(delta_s <= 0) if delta_s is not None else True,
                    "top_speed_kmh": float(np.max(sim_telem.v_kmh)),
                    "top_speed_mph": float(np.max(sim_telem.v_kmh) * 0.621371),
                    "electric_hp": round((params.p_mguk_deploy_max / 1e3) * 1.34102),
                    "battery_finish_soc": float(sim_telem.soc_percent[-1]),
                    "energy_regen_mj": float(sim_telem.net_energy_harvested_mj),
                    "calc_time_ms": round(calc_time_ms, 1)
                },
                "telemetry": {
                    "distance": [round(float(s), 1) for s in s_target],
                    "speed_2026": [round(float(v), 1) for v in speed_2026],
                    "speed_2024": [round(float(v), 1) for v in speed_2024] if speed_2024 is not None else None,
                    "throttle": [round(float(t), 1) for t in throttle],
                    "brake": [round(float(b), 1) for b in brake],
                    "gear": [int(g) for g in gear],
                    "rpm": [round(float(r), 0) for r in rpm],
                    "p_ice_kw": [round(float(p), 1) for p in p_ice],
                    "p_mguk_kw": [round(float(p), 1) for p in p_mguk],
                    "soc_pct": [round(float(b), 1) for b in soc],
                    "tire_temp": [round(float(t), 1) for t in t_tire],
                    "front_load_kg": [round(float(f), 0) for f in front_load_kg],
                    "rear_load_kg": [round(float(r), 0) for r in rear_load_kg],
                    "downforce_kg": [round(float(d), 0) for d in downforce_kg]
                },
                "track_map": map_pts,
                "sectors": [{"name": sec[0], "start": float(sec[1]), "end": float(sec[2])} for sec in getattr(track, "sectors", [])]
            }

            self.send_json(response_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_json({"error": str(e)}, status=500)

    def serve_static(self, path):
        frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
        if not os.path.exists(frontend_dist):
            # Show a helpful status message if dist is not built yet
            msg = (
                "<html><head><title>F1 2026 API Server</title></head>"
                "<body style='font-family:sans-serif; background:#0b0f19; color:#f0f6fc; padding:40px;'>"
                "<h2>🏎️ F1 2026 Simulation API Server is Active</h2>"
                "<p>API Endpoints:</p>"
                "<ul>"
                "<li><code>GET /api/tracks</code> - All 24 calendar tracks with 2024 pole benchmarks</li>"
                "<li><code>POST /api/simulate</code> - 100 Hz Forward-Euler ODE solver & telemetry</li>"
                "</ul>"
                "<p>Vite Dev Server is running on port <strong>5173</strong>.</p>"
                "</body></html>"
            )
            body = msg.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        rel_path = path.lstrip("/") or "index.html"
        full_path = os.path.join(frontend_dist, rel_path)

        if not os.path.exists(full_path):
            full_path = os.path.join(frontend_dist, "index.html")

        mime_type, _ = mimetypes.guess_type(full_path)
        mime_type = mime_type or "application/octet-stream"

        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(404, "File not found")


def run_server(port=8000):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, F1SimulationHandler)
    print(f"[F1-API] Server started on http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("[F1-API] Server stopped.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
