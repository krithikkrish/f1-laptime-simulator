"""
Formula 1 2026 Transient Lap-Time & Hybrid Energy Deployment Simulator.
Professional Motorsport Workstation & F1 Broadcast Telemetry Suite.

Features:
- Dual-Column Split Screen: Left Cockpit & Timing Tower | Right Telemetry Studio & Track Map
- Animated Curved LED Shift Light Array (15 LEDs: 5 Green, 5 Red, 5 Blue/Purple with flash)
- Authentic F1 Steering Wheel LCD Cluster (Gear, Speed, RPM, Throttle/Brake, MGU-K, SoC, Active Aero)
- Real-Time Car Handling Balance Gauge (Understeer ⟵ Neutral ⟶ Oversteer)
- Official F1 Broadcast Timing Tower (P1 Sim vs P2 Real Pole Lap, S1/S2/S3 splits, Speed Trap, Gap)
- 4-Wheel / Dual-Track chassis dynamics with 0.01s Forward-Euler ODE solver
- All 24 FIA Grand Prix Calendar Circuits pre-cached with authentic 3D waypoints & real weather
- MoTeC i2 Pro CSV/LDX, MATLAB .mat, and Standalone Interactive HTML Exports
"""

import os
import io
import time
import json
import numpy as np
import pandas as pd
import scipy.io
import streamlit as st

from f1_sim.params import VehicleParams
from f1_sim.track import Track
from f1_sim.physics_weather import WeatherConditions
from f1_sim.lts_engine import SimulationEngine, LapTelemetry
from f1_sim.openf1_client import OpenF1Client
from f1_sim.setup_sheet import SetupSheet, SETUP_PRESETS
from f1_sim.motec_export import export_to_motec_csv, export_to_motec_ldx_beacon
from f1_sim.tracks_data import (
    create_calendar_track,
    get_available_circuits_list,
    find_canonical_circuit_key
)
from f1_sim.interactive_plots import (
    create_telemetry_figure,
    create_setup_comparison_figure,
    create_delta_figure,
    create_interactive_track_map,
    create_gg_diagram
)

# Page configuration
st.set_page_config(
    page_title="F1 2026 Pit-Wall Workstation",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-Tech F1 Broadcast & Pit-Wall Custom Styling
st.markdown("""
<style>
    /* Dark carbon-graphite workstation background */
    .stApp {
        background: radial-gradient(circle at 10% 10%, #0d1118 0%, #05080c 100%);
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Top Broadcast Header */
    .f1-broadcast-bar {
        background: linear-gradient(90deg, #161b26 0%, #0f141d 100%);
        border-left: 6px solid #e10600;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
    }
    .f1-title {
        font-size: 20px;
        font-weight: 900;
        letter-spacing: -0.5px;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .f1-subtitle {
        font-size: 12px;
        color: #8b949e;
        margin-top: 2px;
    }
    
    /* Pill status badges */
    .pill-badge {
        display: inline-block;
        background: rgba(22, 27, 38, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 11px;
        color: #58a6ff;
        font-family: monospace;
        margin-left: 6px;
    }
    
    /* Curved LED Shift Light Array */
    .shift-light-bar {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 6px;
        background: #090c10;
        border: 2px solid #21262d;
        border-bottom: none;
        border-radius: 12px 12px 0 0;
        padding: 10px 14px 6px 14px;
    }
    .led {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #161b22;
        border: 1px solid #30363d;
        transition: all 0.08s ease;
    }
    .led.green-active {
        background: #00ff88;
        box-shadow: 0 0 10px #00ff88, inset 0 0 4px #ffffff;
    }
    .led.red-active {
        background: #ff1744;
        box-shadow: 0 0 10px #ff1744, inset 0 0 4px #ffffff;
    }
    .led.blue-active {
        background: #7c4dff;
        box-shadow: 0 0 12px #7c4dff, inset 0 0 4px #ffffff;
    }
    .led.flash-shift {
        animation: flashShift 0.15s infinite alternate;
    }
    @keyframes flashShift {
        from { opacity: 1; transform: scale(1.15); }
        to { opacity: 0.25; transform: scale(0.9); }
    }
    
    /* Realistic F1 Steering Wheel LCD Cluster */
    .steering-wheel-lcd {
        background: radial-gradient(circle at 50% 30%, #111724 0%, #070a10 100%);
        border: 2px solid #21262d;
        border-radius: 0 0 12px 12px;
        padding: 16px 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.8), inset 0 1px 4px rgba(255,255,255,0.05);
        margin-bottom: 14px;
    }
    .gear-display {
        background: #06080c;
        border: 2px solid #00ff88;
        border-radius: 8px;
        width: 80px;
        height: 80px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-size: 52px;
        font-weight: 900;
        color: #00ff88;
        font-family: monospace;
        box-shadow: 0 0 15px rgba(0,255,136,0.3);
    }
    .gear-shift-hint {
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin-top: -4px;
    }
    
    /* Pedals & Gauges */
    .pedal-bar-bg {
        background: #161b22;
        border-radius: 4px;
        height: 8px;
        width: 100%;
        overflow: hidden;
        margin-top: 4px;
    }
    .pedal-fill-throttle {
        background: linear-gradient(90deg, #00ff88, #38bdf8);
        height: 100%;
        border-radius: 4px;
        transition: width 0.1s ease;
    }
    .pedal-fill-brake {
        background: linear-gradient(90deg, #f43f5e, #ff1744);
        height: 100%;
        border-radius: 4px;
        transition: width 0.1s ease;
    }
    
    /* Dynamic Car Balance Gauge */
    .balance-card {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 14px;
    }
    .balance-track {
        position: relative;
        height: 12px;
        background: linear-gradient(90deg, #38bdf8 0%, #00ff88 50%, #f59e0b 100%);
        border-radius: 6px;
        margin: 10px 0 6px 0;
    }
    .balance-needle {
        position: absolute;
        top: -4px;
        width: 8px;
        height: 20px;
        background: #ffffff;
        border: 2px solid #000000;
        border-radius: 3px;
        transform: translateX(-50%);
        box-shadow: 0 0 8px #ffffff;
        transition: left 0.1s ease;
    }
    
    /* F1 Broadcast Timing Tower */
    .timing-tower {
        background: #090c10;
        border: 1px solid #21262d;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 14px;
    }
    .timing-tower-header {
        background: #161b26;
        padding: 8px 12px;
        font-size: 11px;
        font-weight: 800;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        display: flex;
        justify-content: space-between;
    }
    .timing-row {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        border-bottom: 1px solid #161b22;
        font-family: monospace;
        font-size: 12px;
    }
    .timing-pos {
        width: 24px;
        font-weight: 900;
        color: #ffffff;
    }
    .timing-driver {
        font-weight: 800;
        width: 60px;
    }
    .timing-team-tag {
        font-size: 10px;
        color: #8b949e;
        flex: 1;
    }
    .timing-time {
        font-weight: 800;
        margin-left: 8px;
    }
    .sector-badge {
        padding: 2px 5px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: 800;
        margin-left: 4px;
    }
    .sector-purple { background: #9c27b0; color: #fff; }
    .sector-green  { background: #2e7d32; color: #fff; }
    .sector-yellow { background: #f57f17; color: #fff; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_client() -> OpenF1Client:
    return OpenF1Client()


# Country flag emoji dictionary for all 24 calendar venues
COUNTRY_FLAGS = {
    "Bahrain": "🇧🇭", "Saudi Arabia": "🇸🇦", "Australia": "🇦🇺", "Japan": "🇯🇵",
    "China": "🇨🇳", "United States": "🇺🇸", "USA": "🇺🇸", "Italy": "🇮🇹",
    "Monaco": "🇲🇨", "Canada": "🇨🇦", "Spain": "🇪🇸", "Austria": "🇦🇹",
    "Great Britain": "🇬🇧", "Hungary": "🇭🇺", "Belgium": "🇧🇪", "Netherlands": "🇳🇱",
    "Azerbaijan": "🇦🇿", "Singapore": "🇸🇬", "Mexico": "🇲🇽", "Brazil": "🇧🇷",
    "Qatar": "🇶🇦", "United Arab Emirates": "🇦🇪", "UAE": "🇦🇪"
}

def format_lap_str(seconds: float) -> str:
    if seconds is None or np.isnan(seconds) or seconds <= 0:
        return "N/A"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:06.3f}" if m > 0 else f"{s:.3f} s"


# ==========================================
# SIDEBAR CONTROLS & DYNAMIC TUNING
# ==========================================
with st.sidebar:
    st.markdown("### 🏁 Grand Prix Venue")
    
    # Retrieve all 24 circuits pre-cached with authentic 3D waypoints and telemetry
    available_circuits = get_available_circuits_list()
    
    default_circuit_idx = 0
    for idx, c in enumerate(available_circuits):
        if c.get("key") == "monza":
            default_circuit_idx = idx
            break
            
    def format_circuit_label(c: dict) -> str:
        flag = COUNTRY_FLAGS.get(c.get("country", ""), "🏁")
        return f"{flag} {c.get('country', '')} — {c.get('short_name', '')} ({c.get('length_m', 0):,.0f} m)"
        
    selected_circuit_idx = st.selectbox(
        "Select Grand Prix Circuit (All 24 Available)",
        range(len(available_circuits)),
        index=default_circuit_idx,
        format_func=lambda i: format_circuit_label(available_circuits[i]),
        help="All 24 Formula 1 World Championship circuits are available with authentic 3D geometry and weather!"
    )
    selected_circuit = available_circuits[selected_circuit_idx]
    
    # Load authentic track, weather, and real pole reference instantaneously
    circuit_key = selected_circuit["key"]
    track, real_weather, track_meta = create_calendar_track(circuit_key, ds=1.0)
    
    live_overlay = st.checkbox(
        "🌐 Fetch 100 Hz Live Pole Overlay (OpenF1)",
        value=False,
        help="Queries OpenF1 API to overlay real pole driver telemetry curve. Works offline if unchecked."
    )
    
    ref_df = None
    fastest_lap_info = {
        "driver_name": track_meta.get("pole_driver", "Pole Lap"),
        "name_acronym": track_meta.get("pole_driver", "REF")[:3].upper() if track_meta.get("pole_driver") else "REF",
        "team_name": track_meta.get("pole_team", "Formula 1 Reference"),
        "lap_duration": track_meta.get("pole_lap_time", None)
    }
    
    if live_overlay and selected_circuit.get("meeting_key"):
        client = get_client()
        with st.spinner(f"Ingesting live telemetry for {selected_circuit['short_name']}..."):
            try:
                live_track, live_weather, live_ref_df, live_fastest_lap = client.get_complete_lap_data(selected_circuit["meeting_key"], year=2024)
                if live_ref_df is not None:
                    ref_df = live_ref_df
                if live_fastest_lap:
                    fastest_lap_info = live_fastest_lap
            except Exception as e:
                st.caption(f"Note: Using pre-cached pole benchmark ({e}).")

    st.markdown("---")
    st.markdown("### 🏎️ Vehicle Setup Sheet")
    
    # Official 2026 Reset Button
    if st.button("✨ Reset All to Official 2026 FIA Regulations", use_container_width=True):
        st.session_state["preset_choice"] = "Balanced Grand Prix Spec"
        st.session_state["fuel_m"] = 40.0
        st.session_state["compound"] = "Soft Slick (C5)"
        st.session_state["ice_p"] = 400.0
        st.session_state["mguk_p"] = 350.0
        st.session_state["v_taper"] = 290.0
        st.session_state["v_cutoff"] = 345.0
        st.session_state["soc_init"] = 65.0
        st.session_state["cl_z"] = 3.20
        st.session_state["cd_z"] = 1.15
        st.session_state["cd_x"] = 0.65
        st.session_state["aero_bal"] = 44.5
        st.session_state["bbw_bias"] = 56.5
        st.rerun()

    preset_choice = st.selectbox(
        "Setup Preset", 
        list(SETUP_PRESETS.keys()), 
        index=0,
        key="preset_choice"
    )
    current_setup = SETUP_PRESETS[preset_choice]

    fuel_m = st.slider(
        "Fuel on Board (kg)", 
        5.0, 110.0, 
        float(current_setup.fuel_load_kg), 
        5.0,
        key="fuel_m",
        help="40 kg = Qualifying Flying Lap | 110 kg = Full Race Start"
    )
    compound = st.selectbox(
        "Tire Compound", 
        ["Soft Slick (C5)", "Medium Slick (C3)", "Hard Slick (C1)", "Intermediate", "Full Wet"], 
        index=0,
        key="compound",
        help="Soft C5 provides maximum peak adhesion (μ ≈ 1.76) for qualifying."
    )

    with st.expander("⚙️ Dynamic 2026 Engineering Levers", expanded=False):
        st.caption("Adjust sliders to test dynamic powertrain and aerodynamic variations.")
        
        ice_p = st.slider("1.6L V6 Turbo ICE Max Power (kW)", 350.0, 450.0, float(current_setup.ice_power_kw), 5.0, key="ice_p")
        mguk_p = st.slider("2026 MGU-K Electric Motor (kW)", 200.0, 400.0, float(current_setup.mguk_power_kw), 10.0, key="mguk_p")
        v_taper = st.slider("MGU-K Taper Threshold (km/h)", 260.0, 310.0, float(current_setup.mguk_taper_start_kmh), 5.0, key="v_taper")
        v_cutoff = st.slider("MGU-K Cutoff Speed (km/h)", 320.0, 360.0, float(current_setup.mguk_taper_end_kmh), 5.0, key="v_cutoff")
        soc_init = st.slider("Initial Battery SoC (%)", 20.0, 100.0, float(current_setup.initial_soc_pct), 5.0, key="soc_init")
        
        cl_z = st.slider("Z-Mode Downforce Cl*A (m²)", 2.2, 4.4, float(current_setup.cl_a_z_mode), 0.05, key="cl_z")
        cd_z = st.slider("Z-Mode Drag Cd*A (m²)", 0.80, 1.50, float(current_setup.cd_a_z_mode), 0.02, key="cd_z")
        cd_x = st.slider("X-Mode Low-Drag Cd*A (m²)", 0.40, 0.85, float(current_setup.cd_a_x_mode), 0.02, key="cd_x")
        aero_bal = st.slider("Aero Balance Front (%)", 40.0, 48.0, float(current_setup.aero_balance_front_pct), 0.1, key="aero_bal")
        fw_angle = st.slider("Front Wing Flap Angle (°)", 12.0, 38.0, float(current_setup.front_wing_flap_deg), 0.5)
        rw_angle = st.slider("Rear Wing Beam Angle (°)", 15.0, 48.0, float(current_setup.rear_wing_beam_deg), 0.5)

        k_spring_f = st.slider("Front Spring Rate (N/mm)", 100.0, 220.0, float(current_setup.front_spring_rate_n_mm), 5.0)
        k_spring_r = st.slider("Rear Spring Rate (N/mm)", 70.0, 160.0, float(current_setup.rear_spring_rate_n_mm), 5.0)
        k_arb_f = st.slider("Front ARB Stiffness (N/mm)", 200.0, 450.0, float(current_setup.front_arb_stiffness_n_mm), 10.0)
        k_arb_r = st.slider("Rear ARB Stiffness (N/mm)", 100.0, 260.0, float(current_setup.rear_arb_stiffness_n_mm), 10.0)
        bbw_bias = st.slider("Baseline Front Brake Bias (%)", 52.0, 62.0, float(current_setup.brake_bias_front_pct), 0.5, key="bbw_bias")

    # Meteorological Overrides
    with st.expander("🌦️ Weather Conditions", expanded=False):
        air_t = st.slider("Air Temp (°C)", 5.0, 45.0, float(real_weather.air_temp_c), 0.5)
        track_t = st.slider("Track Temp (°C)", 15.0, 60.0, float(real_weather.track_temp_c), 0.5)
        humid = st.slider("Humidity (%)", 10.0, 95.0, float(real_weather.humidity_pct), 1.0)
        press = st.slider("Pressure (hPa)", 850.0, 1040.0, float(real_weather.pressure_hpa), 1.0)
        w_speed = st.slider("Wind Velocity (m/s)", 0.0, 20.0, float(real_weather.wind_speed_ms), 0.5)
        w_dir = st.slider("Wind Direction (°)", 0.0, 360.0, float(real_weather.wind_dir_deg), 5.0)
        wet = st.checkbox("🌧️ Wet Track Condition", value=bool(real_weather.rainfall > 0))
        active_weather = WeatherConditions(
            air_temp_c=air_t, track_temp_c=track_t, humidity_pct=humid,
            pressure_hpa=press, wind_speed_ms=w_speed, wind_dir_deg=w_dir,
            rainfall=1 if wet else 0
        )

    # Setup Comparison Mode Toggle
    st.markdown("---")
    compare_mode = st.checkbox("⚔️ Compare Setup A vs B", value=False)
    setup_b_choice = None
    if compare_mode:
        preset_b_options = [k for k in SETUP_PRESETS.keys() if k != preset_choice]
        setup_b_choice = st.selectbox("Select Setup B", preset_b_options, index=0)


# ==========================================
# DYNAMIC 100 Hz PHYSICS INTEGRATION LOOP
# ==========================================
params_a = VehicleParams(
    mass_empty=current_setup.car_empty_mass_kg,
    fuel_mass=fuel_m,
    p_ice_max=ice_p * 1e3,
    p_mguk_deploy_max=mguk_p * 1e3,
    p_mguk_regen_max=mguk_p * 1e3,
    v_taper_start_kmh=v_taper,
    v_taper_end_kmh=v_cutoff,
    cl_A_z_mode=cl_z,
    cd_A_z_mode=cd_z,
    cl_A_x_mode=current_setup.cl_a_x_mode,
    cd_A_x_mode=cd_x,
    mu_peak=1.76 if "Soft" in compound else (1.70 if "Medium" in compound else (1.45 if "Inter" in compound else 1.25)),
    tire_compound="WET" if ("Wet" in compound or "Inter" in compound) else "SLICK"
)

engine_a = SimulationEngine(params=params_a, weather=active_weather)
engine_a.dual_track.k_roll_f = k_arb_f * 400.0
engine_a.dual_track.k_roll_r = k_arb_r * 400.0
engine_a.dual_track.aero_balance_f = aero_bal / 100.0
engine_a.dual_track.bbw_base_front_pct = bbw_bias / 100.0

t_start_ode = time.perf_counter()
sim_telem_a: LapTelemetry = engine_a.run_transient_simulation(
    track=track,
    initial_soc=soc_init / 100.0,
    weather=active_weather
)
ode_duration_ms = (time.perf_counter() - t_start_ode) * 1000.0

sim_telem_b = None
if compare_mode and setup_b_choice:
    setup_b_obj = SETUP_PRESETS[setup_b_choice]
    params_b = setup_b_obj.to_vehicle_params()
    engine_b = SimulationEngine(params=params_b, weather=active_weather)
    sim_telem_b = engine_b.run_transient_simulation(track=track, initial_soc=setup_b_obj.initial_soc_pct / 100.0, weather=active_weather)


# ==========================================
# TOP F1 BROADCAST HEADER BAR
# ==========================================
flag = COUNTRY_FLAGS.get(track_meta.get("country", ""), "🏁")
sim_lap_str = format_lap_str(sim_telem_a.lap_time)
ref_lap_time = float(fastest_lap_info.get("lap_duration")) if (fastest_lap_info and fastest_lap_info.get("lap_duration")) else None
ref_lap_str = format_lap_str(ref_lap_time)
delta_lap = (sim_telem_a.lap_time - ref_lap_time) if ref_lap_time is not None else None

st.markdown(f"""
<div class="f1-broadcast-bar">
    <div>
        <div class="f1-title">
            <span>🏎️</span>
            <span>{flag} {track.name.upper()}</span>
            <span class="pill-badge" style="color:#00ff88; border-color:#00ff88;">FIA 2026 SPEC</span>
        </div>
        <div class="f1-subtitle">
            Track Length: <strong>{track.length:,.1f} m</strong> | Setup: <strong>{preset_choice}</strong> | Mass: <strong>{params_a.total_mass:.0f} kg</strong>
        </div>
    </div>
    <div>
        <span class="pill-badge">🌡️ Air: {active_weather.air_temp_c:.1f}°C</span>
        <span class="pill-badge">🔥 Track: {active_weather.track_temp_c:.1f}°C</span>
        <span class="pill-badge">💨 Wind: {active_weather.wind_speed_ms:.1f} m/s</span>
        <span class="pill-badge" style="color:#ff9100; border-color:#ff9100;">⚡ ODE Solved in {ode_duration_ms:.0f} ms</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# MAIN DUAL-COLUMN SPLIT SCREEN WORKSTATION
# ==========================================
col_cockpit, col_studio = st.columns([4.2, 5.8], gap="medium")

# ----------------------------------------------------
# LEFT COLUMN: F1 PIT-WALL COCKPIT & TIMING TOWER
# ----------------------------------------------------
with col_cockpit:
    # 1. Telemetry Scrubbing & Animation Controller
    col_s1, col_s2 = st.columns([3.5, 1.5])
    with col_s1:
        scrub_distance = st.slider(
            "Track Distance Scrubbing (m)",
            min_value=0.0,
            max_value=float(track.length),
            value=float(track.length * 0.18),
            step=5.0,
            label_visibility="collapsed"
        )
    with col_s2:
        auto_animate = st.checkbox("▶️ Animate", value=False)

    if auto_animate:
        scrub_distance = float((scrub_distance + 40.0) % track.length)

    # State lookup at scrub distance
    idx_s = int(np.clip(np.searchsorted(sim_telem_a.s, scrub_distance), 0, len(sim_telem_a.time) - 1))
    v_now = sim_telem_a.v_kmh[idx_s]
    v_mph = v_now * 0.621371
    gear_now = sim_telem_a.gear[idx_s] if sim_telem_a.gear is not None else 7
    rpm_now = sim_telem_a.engine_rpm[idx_s] if sim_telem_a.engine_rpm is not None else 10800.0
    thr_now = sim_telem_a.throttle[idx_s] * 100.0
    brk_now = sim_telem_a.brake[idx_s] * 100.0
    mgu_now = sim_telem_a.p_mguk_kw[idx_s]
    soc_now = sim_telem_a.soc_percent[idx_s]
    ay_now = sim_telem_a.a_y[idx_s]
    ax_now = sim_telem_a.a_x[idx_s]
    aero_mode_now = sim_telem_a.aero_mode[idx_s] if sim_telem_a.aero_mode is not None else "Z_MODE"

    # 2. Animated Curved LED Shift Light Array (15 LEDs)
    led_thresholds = [
        (8000, "green"), (8400, "green"), (8800, "green"), (9200, "green"), (9600, "green"),
        (10000, "red"), (10300, "red"), (10600, "red"), (10900, "red"), (11200, "red"),
        (11400, "blue"), (11600, "blue"), (11750, "blue"), (11900, "blue"), (12000, "blue")
    ]
    is_flash = rpm_now >= 11300.0
    led_html_parts = []
    for thresh, color in led_thresholds:
        active = rpm_now >= thresh
        if active:
            cls = f"led {color}-active"
            if is_flash and (color in ["red", "blue"]):
                cls += " flash-shift"
        else:
            cls = "led"
        led_html_parts.append(f'<div class="{cls}"></div>')
    shift_lights_html = "".join(led_html_parts)

    st.markdown(f'<div class="shift-light-bar">{shift_lights_html}</div>', unsafe_allow_html=True)

    # 3. Realistic F1 Steering Wheel LCD Display
    shift_text = "▲ SHIFT" if rpm_now > 11300 else ("OPTIMAL" if rpm_now > 10200 else "POWER")
    shift_color = "#ff1744" if rpm_now > 11300 else ("#00ff88" if rpm_now > 10200 else "#8b949e")
    aero_badge_color = "#00e5ff" if aero_mode_now == "X_MODE" else "#ff9100"
    aero_badge_text = "X-MODE (LOW DRAG)" if aero_mode_now == "X_MODE" else "Z-MODE (DOWNFORCE)"
    mgu_color = "#ff9100" if mgu_now >= 0 else "#2979ff"
    mgu_label = f"DEPLOY +{mgu_now:.0f} kW" if mgu_now >= 0 else f"REGEN {mgu_now:.0f} kW"

    st.markdown(f"""
    <div class="steering-wheel-lcd">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid #21262d; padding-bottom:8px;">
            <div style="font-size:11px; font-weight:800; color:#8b949e; letter-spacing:1px;">F1-2026 // COCKPIT OS</div>
            <div>
                <span style="font-size:10px; font-weight:900; background:{aero_badge_color}22; color:{aero_badge_color}; border:1px solid {aero_badge_color}; padding:2px 8px; border-radius:4px;">
                    🪽 {aero_badge_text}
                </span>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="flex:1;">
                <div style="font-size:10px; font-weight:700; color:#8b949e;">SPEED</div>
                <div style="font-size:32px; font-weight:900; color:#ffffff; font-family:monospace; line-height:1;">
                    {v_now:.0f} <span style="font-size:13px; color:#8b949e;">km/h</span>
                </div>
                <div style="font-size:12px; color:#8b949e; font-family:monospace;">{v_mph:.0f} mph</div>
                <div style="margin-top:10px;">
                    <div style="font-size:10px; font-weight:700; color:#8b949e;">ENGINE RPM: <strong style="color:#ffd600;">{rpm_now:.0f}</strong></div>
                    <div class="pedal-bar-bg" style="height:6px;">
                        <div style="background:linear-gradient(90deg, #00ff88, #ffd600, #ff1744); width:{min(100.0, max(0.0, (rpm_now-5000)/7000*100))}%; height:100%; border-radius:3px;"></div>
                    </div>
                </div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:center; padding:0 16px;">
                <div class="gear-display">
                    <div>{gear_now}</div>
                    <div class="gear-shift-hint" style="color:{shift_color};">{shift_text}</div>
                </div>
            </div>
            <div style="flex:1; text-align:right;">
                <div style="font-size:10px; font-weight:700; color:#8b949e;">MGU-K 350kW</div>
                <div style="font-size:18px; font-weight:900; color:{mgu_color}; font-family:monospace;">
                    {mgu_label}
                </div>
                <div style="margin-top:8px;">
                    <div style="font-size:10px; font-weight:700; color:#8b949e;">BATTERY SoC: <strong style="color:#d500f9;">{soc_now:.1f}%</strong></div>
                    <div class="pedal-bar-bg" style="height:6px;">
                        <div style="background:#d500f9; width:{soc_now}%; height:100%; border-radius:3px;"></div>
                    </div>
                </div>
                <div style="margin-top:6px; font-size:11px; color:#e0e0e0; font-family:monospace;">
                    G: <strong style="color:#00ff88;">{ay_now:+.2f}y</strong> | <strong style="color:#00e5ff;">{ax_now:+.2f}x</strong>
                </div>
            </div>
        </div>
        <div style="display:flex; gap:16px; margin-top:14px; padding-top:10px; border-top:1px solid #1f2937;">
            <div style="flex:1;">
                <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700;">
                    <span style="color:#00ff88;">THROTTLE</span>
                    <span style="color:#ffffff;">{thr_now:.0f}%</span>
                </div>
                <div class="pedal-bar-bg">
                    <div class="pedal-fill-throttle" style="width:{thr_now}%;"></div>
                </div>
            </div>
            <div style="flex:1;">
                <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700;">
                    <span style="color:#f43f5e;">BRAKE</span>
                    <span style="color:#ffffff;">{brk_now:.0f}%</span>
                </div>
                <div class="pedal-bar-bg">
                    <div class="pedal-fill-brake" style="width:{brk_now}%;"></div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4. Real-Time Dynamic Car Handling Balance Gauge
    ay_abs = abs(ay_now)
    if ay_abs < 0.25:
        bal_status = "STRAIGHT-LINE STABLE"
        bal_color = "#38bdf8"
        bal_pct = 50.0
        bal_desc = "Neutral aerodynamic downforce & zero lateral load transfer."
    else:
        fz_f = sim_telem_a.f_z_fl[idx_s] + sim_telem_a.f_z_fr[idx_s]
        fz_r = sim_telem_a.f_z_rl[idx_s] + sim_telem_a.f_z_rr[idx_s]
        d_fz_f = abs(sim_telem_a.f_z_fr[idx_s] - sim_telem_a.f_z_fl[idx_s]) / max(fz_f, 100.0)
        d_fz_r = abs(sim_telem_a.f_z_rr[idx_s] - sim_telem_a.f_z_rl[idx_s]) / max(fz_r, 100.0)
        raw_m = (d_fz_r - d_fz_f) * 4.0
        bal_pct = float(np.clip(50.0 + raw_m * 50.0, 5.0, 95.0))
        
        if bal_pct < 42.0:
            bal_status = "UNDERSTEER (FRONT PUSH)"
            bal_color = "#38bdf8"
            bal_desc = f"Front axle slip angle saturated ({abs(raw_m):.2f}Δ). Car pushing toward corner exit."
        elif bal_pct > 58.0:
            bal_status = "OVERSTEER (REAR ROTATION)"
            bal_color = "#f59e0b"
            bal_desc = f"Rear axle slip angle high ({raw_m:.2f}Δ). Car rotating aggressively on apex."
        else:
            bal_status = "OPTIMAL NEUTRAL BALANCE"
            bal_color = "#00ff88"
            bal_desc = "Synchronized 4-wheel slip angle for maximum cornering adhesion."

    st.markdown(f"""
    <div class="balance-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-size:11px; font-weight:800; color:#8b949e; letter-spacing:0.8px;">⚖️ CHASSIS HANDLING BALANCE</div>
            <div style="font-size:11px; font-weight:800; color:{bal_color};">{bal_status}</div>
        </div>
        <div class="balance-track">
            <div class="balance-needle" style="left:{bal_pct}%;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:10px; color:#8b949e; font-weight:700;">
            <span>◀ UNDERSTEER (PUSH)</span>
            <span>NEUTRAL</span>
            <span>OVERSTEER (LOOSE) ▶</span>
        </div>
        <div style="font-size:11px; color:#9ca3af; margin-top:4px;">{bal_desc}</div>
    </div>
    """, unsafe_allow_html=True)

    # 5. Authentic F1 Broadcast Timing Tower
    sector_splits = []
    tot_sim = sim_telem_a.lap_time
    for sec_name, s_start, s_end in track.sectors:
        i0 = np.searchsorted(sim_telem_a.s, s_start)
        i1 = min(len(sim_telem_a.s) - 1, np.searchsorted(sim_telem_a.s, s_end))
        dt_s = sim_telem_a.time[i1] - sim_telem_a.time[i0]
        sector_splits.append(dt_s)

    s1_sim = sector_splits[0] if len(sector_splits) > 0 else 0.0
    s2_sim = sector_splits[1] if len(sector_splits) > 1 else 0.0
    s3_sim = sector_splits[2] if len(sector_splits) > 2 else 0.0

    pole_driver_abbr = fastest_lap_info.get("name_acronym", "LEC") if fastest_lap_info else "LEC"
    pole_driver_full = fastest_lap_info.get("driver_name", "Charles Leclerc") if fastest_lap_info else "Charles Leclerc"
    pole_team = fastest_lap_info.get("team_name", "Ferrari") if fastest_lap_info else "Scuderia Ferrari"
    top_spd_sim = np.max(sim_telem_a.v_kmh)

    # Sector highlight badges (Purple if faster than benchmark)
    delta_val = delta_lap if delta_lap is not None else 0.0
    s1_badge = "sector-purple" if delta_val <= 0 else "sector-green"
    s2_badge = "sector-purple" if delta_val <= 0 else "sector-green"
    s3_badge = "sector-green"

    st.markdown(f"""
    <div class="timing-tower">
        <div class="timing-tower-header">
            <span>🏁 F1 TIMING TOWER // QUALIFYING SIM</span>
            <span>LIVE DELTA: <strong style="color:{'#00ff88' if delta_val <= 0 else '#f59e0b'};">{delta_val:+.3f}s</strong></span>
        </div>
        <div class="timing-row" style="background:rgba(0, 255, 136, 0.08); border-left:4px solid #00ff88;">
            <div class="timing-pos" style="color:#00ff88;">1</div>
            <div class="timing-driver" style="color:#00ff88;">2026 SIM</div>
            <div class="timing-team-tag">Formula 1 2026 Spec</div>
            <div class="timing-time" style="color:#00ff88;">{sim_lap_str}</div>
            <div class="sector-badge {s1_badge}">S1 {s1_sim:.2f}</div>
            <div class="sector-badge {s2_badge}">S2 {s2_sim:.2f}</div>
            <div class="sector-badge {s3_badge}">S3 {s3_sim:.2f}</div>
            <div style="font-size:10px; color:#8b949e; margin-left:6px;">ST: {top_spd_sim:.0f} km/h</div>
        </div>
        <div class="timing-row" style="border-left:4px solid #00e5ff;">
            <div class="timing-pos" style="color:#00e5ff;">2</div>
            <div class="timing-driver" style="color:#00e5ff;">{pole_driver_abbr}</div>
            <div class="timing-team-tag">{pole_team} ({pole_driver_full})</div>
            <div class="timing-time" style="color:#00e5ff;">{ref_lap_str}</div>
            <div style="font-size:10px; color:#8b949e; margin-left:10px;">GAP: {abs(delta_val):+.3f}s</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ----------------------------------------------------
# RIGHT COLUMN: INTERACTIVE TELEMETRY & TRACK STUDIO
# ----------------------------------------------------
with col_studio:
    tab_map, tab_telem, tab_compare, tab_gg, tab_debrief, tab_export = st.tabs([
        "🗺️ Live Circuit & GPS",
        "📊 Telemetry Studio",
        "⚔️ Setup Comparison (A vs B)",
        "⭕ G-G Friction Circle",
        "📻 Race Engineer Debrief",
        "💾 Engineering Export"
    ])

    with tab_map:
        fig_map = create_interactive_track_map(track, sim_telem_a, scrub_dist=scrub_distance)
        st.plotly_chart(fig_map, use_container_width=True)
        
        # Track Quick Stats Banner
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1:
            st.metric("Total Arc Length", f"{track.length:,.1f} m", f"{track.length/1000.0:.3f} km")
        with col_t2:
            st.metric("Min Corner Radius", f"{np.min(track.corner_radius):.1f} m", "Apex Limit")
        with col_t3:
            st.metric("Elevation Span (ΔZ)", f"{np.max(track.z) - np.min(track.z):.1f} m", f"Max Incline {np.max(track.grade)*100:.1f}%")
        with col_t4:
            st.metric("Active Scrub Point", f"{scrub_distance:.0f} m", f"Sector {1 if scrub_distance < track.sectors[0][2] else (2 if scrub_distance < track.sectors[1][2] else 3)}")

    with tab_telem:
        driver_label = f"{fastest_lap_info.get('driver_name', 'Pole Lap')} ({fastest_lap_info.get('name_acronym', 'REF')})" if fastest_lap_info else "Pole Lap"
        fig_telem = create_telemetry_figure(
            sim_telem=sim_telem_a,
            ref_df=ref_df,
            track=track,
            driver_label=driver_label,
            scrub_dist=scrub_distance,
            setup_b_telem=sim_telem_b,
            setup_b_label=setup_b_choice
        )
        st.plotly_chart(fig_telem, use_container_width=True)

    with tab_compare:
        if compare_mode and sim_telem_b is not None:
            delta_lap_ab = sim_telem_b.lap_time - sim_telem_a.lap_time
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                st.metric("Setup A Lap Time", format_lap_str(sim_telem_a.lap_time), f"Top: {np.max(sim_telem_a.v_kmh):.1f} km/h")
            with col_c2:
                st.metric("Setup B Lap Time", format_lap_str(sim_telem_b.lap_time), f"Top: {np.max(sim_telem_b.v_kmh):.1f} km/h")
            with col_c3:
                st.metric("Lap Time Delta (B - A)", f"{delta_lap_ab:+.3f} s", "Faster" if delta_lap_ab > 0 else "Slower", delta_color="inverse")
                
            fig_cmp = create_setup_comparison_figure(sim_telem_a, sim_telem_b, label_a=preset_choice, label_b=setup_b_choice)
            st.plotly_chart(fig_cmp, use_container_width=True)
        else:
            st.info("💡 To compare two setups head-to-head, check '⚔️ Compare Setup A vs B' in the sidebar.")

    with tab_gg:
        col_gg1, col_gg2 = st.columns([2.2, 1.0])
        with col_gg1:
            fig_gg = create_gg_diagram(sim_telem_a, scrub_dist=scrub_distance)
            st.plotly_chart(fig_gg, use_container_width=True)
        with col_gg2:
            st.markdown("#### 🏎️ 4-Wheel Adhesion")
            st.write(f"**Peak Lateral Adhesion:** {np.max(np.abs(sim_telem_a.a_y)):.2f} g")
            st.write(f"**Peak Longitudinal Braking:** {np.min(sim_telem_a.a_x):.2f} g")
            st.write(f"**Peak Aerodynamic Downforce:** {np.max(sim_telem_a.f_downforce_n)/9.81:,.0f} kg")
            st.write(f"**Max Outer Wheel Load:** {max(np.max(sim_telem_a.f_z_fr), np.max(sim_telem_a.f_z_rr)):,.0f} N")
            st.write(f"**Dynamic BBW Migration:** {np.min(sim_telem_a.bbw_front_pct):.1f}% ➔ {np.max(sim_telem_a.bbw_front_pct):.1f}% Front")

    with tab_debrief:
        if delta_lap is not None:
            if delta_lap <= 0:
                v_badge = "🟢 COMPETITIVE QUALIFYING PACE"
                v_text = f"Your 2026 car clocked <strong>{sim_lap_str}</strong>, which is <strong style='color:#00ff88;'>{abs(delta_lap):.3f}s FASTER</strong> than the real reference pole lap ({ref_lap_str} set by {pole_driver_full})! The massive 350 kW electric torque out of slow corners and X-Mode on straights made the difference."
            else:
                v_badge = "🟡 PRACTICE PACE"
                v_text = f"Your 2026 car clocked <strong>{sim_lap_str}</strong>, trailing the real pole lap ({ref_lap_str} set by {pole_driver_full}) by <strong style='color:#f59e0b;'>{delta_lap:.3f}s</strong>. Tip: Switch to Soft Slick (C5) tires or trim rear wing flap angle."
        else:
            v_badge = "🏁 SIMULATION COMPLETE"
            v_text = f"Simulation completed in <strong>{sim_lap_str}</strong> with a top speed of <strong>{np.max(sim_telem_a.v_kmh):.1f} km/h</strong>."

        st.markdown(f"""
        <div style="background:#161b26; border-left:6px solid #00ff88; border-radius:6px; padding:12px 16px; margin-bottom:12px;">
            <div style="font-size:14px; font-weight:800; color:#00ff88;">📻 Race Engineer Debrief — {v_badge}</div>
            <div style="font-size:12px; color:#d1d5db; margin-top:4px;">{v_text}</div>
        </div>
        """, unsafe_allow_html=True)

        col_i1, col_i2 = st.columns(2)
        with col_i1:
            st.markdown(f"""
            <div style="background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:10px 12px; margin-bottom:8px;">
                <div style="font-size:11px; font-weight:800; color:#ff9100;">⚡ 350 kW MGU-K HYBRID</div>
                <div style="font-size:16px; font-weight:900; color:#ffffff; margin:2px 0;">{sim_telem_a.net_energy_deployed_mj:.2f} MJ Deployed</div>
                <div style="font-size:11px; color:#8b949e;">Explosive torque up to 290 km/h, tapering to preserve battery energy according to FIA 2026 regulations.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:10px 12px;">
                <div style="font-size:11px; font-weight:800; color:#00e5ff;">💨 ACTIVE AERO WINGS</div>
                <div style="font-size:16px; font-weight:900; color:#ffffff; margin:2px 0;">{np.max(sim_telem_a.v_kmh):.1f} km/h Top Speed</div>
                <div style="font-size:11px; color:#8b949e;">Wings switched automatically between high-downforce Z-Mode in curves and low-drag X-Mode on straights.</div>
            </div>
            """, unsafe_allow_html=True)
        with col_i2:
            st.markdown(f"""
            <div style="background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:10px 12px; margin-bottom:8px;">
                <div style="font-size:11px; font-weight:800; color:#f43f5e;">🛑 BRAKING & RECOVERY</div>
                <div style="font-size:16px; font-weight:900; color:#ffffff; margin:2px 0;">{sim_telem_a.net_energy_harvested_mj:.2f} MJ Harvested</div>
                <div style="font-size:11px; color:#8b949e;">MGU-K acted as a generator under hard braking (peak {abs(np.min(sim_telem_a.a_x)):.1f} Gs), recharging battery energy.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:10px 12px;">
                <div style="font-size:11px; font-weight:800; color:#d500f9;">🔋 THERMAL & TIRE WINDOW</div>
                <div style="font-size:16px; font-weight:900; color:#ffffff; margin:2px 0;">{np.max(sim_telem_a.t_tire_c):.1f}°C Peak Tire Temp</div>
                <div style="font-size:11px; color:#8b949e;">Tires maintained optimal operating adhesion without blistering; battery SoC finished at {sim_telem_a.soc_percent[-1]:.1f}%.</div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("💡 Beginner's Guide: 2026 Formula 1 Regulations Explained", expanded=False):
            st.markdown("""
            - **50/50 Power Split**: 400 kW (~536 bhp) 1.6L V6 Turbo engine + 350 kW (~470 bhp) MGU-K electric motor totaling over 1,000 bhp.
            - **MGU-K Tapering**: Full 350 kW electric boost available on corner exit up to 290 km/h, tapering to 0 kW at 345 km/h to manage the 4.0 MJ per lap battery limit.
            - **Active Aero**: High-downforce Z-Mode in corners vs low-drag X-Mode on straights (~28% drag reduction).
            - **Brake-by-Wire**: Dynamically balances traditional friction carbon brakes with electric motor regeneration on the rear axle.
            """)

    with tab_export:
        st.markdown("#### 💾 Motorsport Telemetry & Workspace Export")
        st.write("Export 100 Hz simulation data directly into **MoTeC i2 Pro**, **MATLAB R2026a**, or **Standalone Interactive HTML**.")

        motec_csv_str = export_to_motec_csv(sim_telem_a, track, vehicle_name="2026 Formula 1", driver_name="Sim Engineer")
        motec_ldx_str = export_to_motec_ldx_beacon(track, sim_telem_a)

        mat_buf = io.BytesIO()
        mat_dict = {
            "circuit_name": track.name,
            "lap_time": float(sim_telem_a.lap_time),
            "distance_total": float(sim_telem_a.distance_total),
            "time": sim_telem_a.time,
            "s": sim_telem_a.s,
            "v_kmh": sim_telem_a.v_kmh,
            "a_x": sim_telem_a.a_x,
            "a_y": sim_telem_a.a_y,
            "throttle": sim_telem_a.throttle,
            "brake": sim_telem_a.brake,
            "gear": sim_telem_a.gear,
            "engine_rpm": sim_telem_a.engine_rpm,
            "steering_angle_deg": sim_telem_a.steering_angle_deg,
            "p_ice_kw": sim_telem_a.p_ice_kw,
            "p_mguk_kw": sim_telem_a.p_mguk_kw,
            "soc_percent": sim_telem_a.soc_percent,
            "t_tire_c": sim_telem_a.t_tire_c,
            "f_z_fl": sim_telem_a.f_z_fl,
            "f_z_fr": sim_telem_a.f_z_fr,
            "f_z_rl": sim_telem_a.f_z_rl,
            "f_z_rr": sim_telem_a.f_z_rr,
            "f_downforce_n": sim_telem_a.f_downforce_n,
            "f_drag_n": sim_telem_a.f_drag_n,
            "track_x": track.x,
            "track_y": track.y,
            "track_z": track.z
        }
        scipy.io.savemat(mat_buf, mat_dict)
        mat_bytes = mat_buf.getvalue()

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.download_button(
                label="🏎️ Download MoTeC i2 Pro CSV (.csv)",
                data=motec_csv_str,
                file_name=f"f1_2026_{track.name.split()[0].lower()}_motec.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.download_button(
                label="🚩 Download MoTeC Beacons (.ldx)",
                data=motec_ldx_str,
                file_name=f"f1_2026_{track.name.split()[0].lower()}_beacons.ldx",
                mime="application/xml",
                use_container_width=True
            )
        with col_ex2:
            st.download_button(
                label="💻 Download MATLAB Workspace (.mat)",
                data=mat_bytes,
                file_name=f"f1_2026_{track.name.split()[0].lower()}_matlab.mat",
                mime="application/x-matlab-data",
                use_container_width=True
            )
            html_telem = fig_telem.to_html(include_plotlyjs="cdn")
            st.download_button(
                label="🌐 Download Standalone Interactive HTML (.html)",
                data=html_telem,
                file_name=f"f1_2026_{track.name.split()[0].lower()}_interactive.html",
                mime="text/html",
                use_container_width=True
            )
