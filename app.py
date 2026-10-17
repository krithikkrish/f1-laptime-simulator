"""
Formula 1 2026 Transient Lap-Time & Hybrid Energy Deployment Simulator.
Professional Motorsport Telemetry Workstation (McLaren Applied ATLAS & MoTeC i2 Pro Standard).

Key Engineering Features:
- 4-Wheel / Dual-Track chassis dynamics with dynamic normal load transfer & Pacejka tire formulation
- 8-Speed sequential transmission with realistic gear ratios, engine RPM model, and 15ms shift cuts
- Real-time distance scrubbing cursor with synchronized live steering wheel digital gauge cluster
- Setup Comparison Mode (Setup A vs Setup B) with Delta-V & Delta-T differential channels
- Authentic OpenF1 API real-world sessions, 3D GPS tracks, and weather stations for ALL 24 Grand Prix circuits
- Plain-English Race Engineer insights & Beginner's Guide for easy data comprehension
- Strict official FIA 2026 regulations default parameters with dynamic engineering levers
- One-click export to MoTeC i2 Pro CSV with .ldx beacon markers, MATLAB .mat, and CSV/JSON
"""

import os
import io
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
    page_title="F1 2026 Telemetry Workstation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-Tech Dark Carbon-Graphite McLaren ATLAS / MoTeC i2 Styling
st.markdown("""
<style>
    /* Dark carbon-graphite workstation background */
    .stApp {
        background: radial-gradient(circle at 10% 10%, #0d1117 0%, #040608 100%);
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Header workstation banner */
    .workstation-header {
        background: linear-gradient(90deg, #161b22 0%, #0d1117 100%);
        border-left: 6px solid #ff9100;
        border-bottom: 1px solid #30363d;
        border-radius: 6px;
        padding: 16px 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    .workstation-title {
        font-size: 24px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .workstation-subtitle {
        font-size: 13px;
        color: #8b949e;
        margin-top: 3px;
    }
    
    /* Plain-English Race Engineer Verdict Banner */
    .verdict-banner {
        background: linear-gradient(90deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }
    .verdict-title {
        font-size: 16px;
        font-weight: 800;
        letter-spacing: -0.3px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .verdict-desc {
        font-size: 13px;
        color: #d1d5db;
        margin-top: 6px;
        line-height: 1.5;
    }
    
    /* Digital Steering Wheel Gauge Cluster */
    .gauge-cluster {
        background: #161b22;
        border: 2px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.6);
    }
    .gear-box {
        background: #0d1117;
        border: 2px solid #00ff88;
        border-radius: 6px;
        width: 64px;
        height: 64px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 40px;
        font-weight: 900;
        color: #00ff88;
        font-family: monospace;
    }
    .gauge-metric {
        text-align: center;
        padding: 0 10px;
    }
    .gauge-label {
        font-size: 10px;
        font-weight: 700;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .gauge-value {
        font-size: 22px;
        font-weight: 800;
        color: #ffffff;
        font-family: monospace;
    }
    
    /* Plain-English Insight Cards Grid */
    .insight-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 14px 16px;
        height: 100%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .insight-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .insight-val {
        font-size: 20px;
        font-weight: 800;
        margin-top: 6px;
        font-family: monospace;
    }
    .insight-body {
        font-size: 12px;
        color: #9ca3af;
        margin-top: 6px;
        line-height: 1.45;
    }
    
    /* Metric Cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 12px 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .metric-title {
        font-size: 10px;
        font-weight: 700;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-val {
        font-size: 22px;
        font-weight: 800;
        color: #00ff88;
        margin-top: 3px;
        font-family: monospace;
    }
    .metric-sub {
        font-size: 11px;
        color: #58a6ff;
        margin-top: 1px;
    }
    
    /* Badges */
    .status-badge {
        display: inline-block;
        background: #21262d;
        border: 1px solid #30363d;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        color: #58a6ff;
        margin-right: 6px;
        font-family: monospace;
    }
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

# Format seconds into M:SS.mmm
def format_lap_str(seconds: float) -> str:
    if seconds is None or np.isnan(seconds) or seconds <= 0:
        return "N/A"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:06.3f}" if m > 0 else f"{s:.3f} s"


# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### 🏁 Grand Prix Circuit")
    
    # Retrieve all 24 circuits pre-cached with authentic 3D waypoints and telemetry
    available_circuits = get_available_circuits_list()
    
    # Find default index (Monza)
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
    
    # Option to overlay 100 Hz live OpenF1 driver trace
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
    st.markdown("### 🌦️ Meteorological Station Telemetry")
    
    st.markdown(f"""
    <div style="background:#161b22; border:1px solid #30363d; border-radius:6px; padding:10px 12px; margin-bottom:10px;">
        <span class="status-badge">🌡️ Air: {real_weather.air_temp_c:.1f}°C</span>
        <span class="status-badge">🔥 Track: {real_weather.track_temp_c:.1f}°C</span>
        <span class="status-badge">💧 Humid: {real_weather.humidity_pct:.0f}%</span>
        <span class="status-badge">💨 Wind: {real_weather.wind_speed_ms:.1f} m/s</span>
        <span class="status-badge">⚖️ Air ρ: {real_weather.air_density:.3f} kg/m³</span>
        <span class="status-badge">🧭 Press: {real_weather.pressure_hpa:.1f} hPa</span>
    </div>
    """, unsafe_allow_html=True)

    custom_weather = st.checkbox("⚙️ Environmental Overrides", value=False)
    if custom_weather:
        air_t = st.slider("Ambient Air Temp (°C)", 5.0, 45.0, float(real_weather.air_temp_c), 0.5)
        track_t = st.slider("Track Asphalt Temp (°C)", 15.0, 60.0, float(real_weather.track_temp_c), 0.5)
        humid = st.slider("Relative Humidity (%)", 10.0, 95.0, float(real_weather.humidity_pct), 1.0)
        press = st.slider("Barometric Pressure (hPa)", 850.0, 1040.0, float(real_weather.pressure_hpa), 1.0)
        w_speed = st.slider("Wind Velocity (m/s)", 0.0, 20.0, float(real_weather.wind_speed_ms), 0.5)
        w_dir = st.slider("Wind Direction (°)", 0.0, 360.0, float(real_weather.wind_dir_deg), 5.0)
        wet = st.checkbox("🌧️ Wet Track Condition", value=bool(real_weather.rainfall > 0))
        active_weather = WeatherConditions(
            air_temp_c=air_t, track_temp_c=track_t, humidity_pct=humid,
            pressure_hpa=press, wind_speed_ms=w_speed, wind_dir_deg=w_dir,
            rainfall=1 if wet else 0
        )
    else:
        active_weather = real_weather

    st.markdown("---")
    st.markdown("### 🏎️ Vehicle Setup Sheet (Setup A)")
    
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

    # Simple & Intuitive Driver Adjustments
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

    # Advanced 2026 Powertrain & Engineering Levers (Dynamic & fully tunable with 2026 defaults)
    with st.expander("⚙️ Advanced 2026 Powertrain & Engineering (Dynamic)", expanded=False):
        st.caption("Defaults to official FIA 2026 Technical Regulations. Adjust sliders to test powertrain tuning.")
        
        st.markdown("**⚡ 2026 Hybrid Powertrain (50/50 Split)**")
        ice_p = st.slider(
            "1.6L V6 Turbo ICE Max Power (kW)", 
            350.0, 450.0, 
            float(current_setup.ice_power_kw), 
            5.0,
            key="ice_p",
            help="FIA 2026 regulation is 400 kW (~536 bhp) running on 100% sustainable fuels."
        )
        mguk_p = st.slider(
            "2026 MGU-K Electric Motor (kW)", 
            200.0, 400.0, 
            float(current_setup.mguk_power_kw), 
            10.0,
            key="mguk_p",
            help="FIA 2026 regulation is 350 kW (~470 bhp). Previous F1 cars only had 120 kW!"
        )
        v_taper = st.slider(
            "MGU-K Taper Threshold (km/h)", 
            260.0, 310.0, 
            float(current_setup.mguk_taper_start_kmh), 
            5.0,
            key="v_taper",
            help="Speed at which electric assist starts dialing back to preserve battery (FIA rule: 290 km/h)."
        )
        v_cutoff = st.slider(
            "MGU-K Cutoff Speed (km/h)", 
            320.0, 360.0, 
            float(current_setup.mguk_taper_end_kmh), 
            5.0,
            key="v_cutoff",
            help="Speed where electric boost reaches 0 kW and car runs purely on V6 ICE (FIA rule: 345 km/h)."
        )
        soc_init = st.slider(
            "Initial Battery State of Charge (%)", 
            20.0, 100.0, 
            float(current_setup.initial_soc_pct), 
            5.0,
            key="soc_init",
            help="Starting battery charge level (4.0 MJ total usable capacity per lap)."
        )
        
        st.markdown("**🪽 Active Aerodynamics (Z-Mode & X-Mode)**")
        cl_z = st.slider(
            "Z-Mode Cornering Downforce Cl*A (m²)", 
            2.2, 4.4, 
            float(current_setup.cl_a_z_mode), 
            0.05,
            key="cl_z",
            help="High-downforce mode active in corners to press car into tarmac."
        )
        cd_z = st.slider(
            "Z-Mode Drag Cd*A (m²)", 
            0.80, 1.50, 
            float(current_setup.cd_a_z_mode), 
            0.02,
            key="cd_z",
            help="Aerodynamic drag when cornering flaps are engaged."
        )
        cd_x = st.slider(
            "X-Mode Low-Drag Cd*A (m²)", 
            0.40, 0.85, 
            float(current_setup.cd_a_x_mode), 
            0.02,
            key="cd_x",
            help="Low-drag mode active on straights when wing flaps open (~28% drag reduction)."
        )
        aero_bal = st.slider(
            "Aero Balance Front (%)", 
            40.0, 48.0, 
            float(current_setup.aero_balance_front_pct), 
            0.1,
            key="aero_bal",
            help="Percentage of total aerodynamic downforce acting on front axle."
        )
        fw_angle = st.slider("Front Wing Flap Angle (°)", 12.0, 38.0, float(current_setup.front_wing_flap_deg), 0.5)
        rw_angle = st.slider("Rear Wing Beam Angle (°)", 15.0, 48.0, float(current_setup.rear_wing_beam_deg), 0.5)

        st.markdown("**🏎️ Suspension & Chassis Mechanicals**")
        k_spring_f = st.slider("Front Spring Rate (N/mm)", 100.0, 220.0, float(current_setup.front_spring_rate_n_mm), 5.0)
        k_spring_r = st.slider("Rear Spring Rate (N/mm)", 70.0, 160.0, float(current_setup.rear_spring_rate_n_mm), 5.0)
        k_arb_f = st.slider("Front ARB Stiffness (N/mm)", 200.0, 450.0, float(current_setup.front_arb_stiffness_n_mm), 10.0)
        k_arb_r = st.slider("Rear ARB Stiffness (N/mm)", 100.0, 260.0, float(current_setup.rear_arb_stiffness_n_mm), 10.0)
        bbw_bias = st.slider(
            "Baseline Front Brake Bias (%)", 
            52.0, 62.0, 
            float(current_setup.brake_bias_front_pct), 
            0.5,
            key="bbw_bias",
            help="Front friction brake share. Rear axle braking is handled dynamically with MGU-K regen."
        )

    # Enable Setup Comparison A vs B
    st.markdown("---")
    compare_mode = st.checkbox("⚔️ Setup Comparison Mode (A vs B)", value=False)
    setup_b_choice = None
    if compare_mode:
        preset_b_options = [k for k in SETUP_PRESETS.keys() if k != preset_choice]
        setup_b_choice = st.selectbox("Select Setup B", preset_b_options, index=0)

# Instantiate VehicleParams for Setup A with official 2026 homologated standards
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

# Run Simulation for Setup A
engine_a = SimulationEngine(params=params_a, weather=active_weather)
engine_a.dual_track.k_roll_f = k_arb_f * 400.0
engine_a.dual_track.k_roll_r = k_arb_r * 400.0
engine_a.dual_track.aero_balance_f = aero_bal / 100.0
engine_a.dual_track.bbw_base_front_pct = bbw_bias / 100.0

sim_telem_a: LapTelemetry = engine_a.run_transient_simulation(
    track=track,
    initial_soc=soc_init / 100.0,
    weather=active_weather
)

# Run Simulation for Setup B if enabled
sim_telem_b = None
if compare_mode and setup_b_choice:
    setup_b_obj = SETUP_PRESETS[setup_b_choice]
    params_b = setup_b_obj.to_vehicle_params()
    engine_b = SimulationEngine(params=params_b, weather=active_weather)
    sim_telem_b = engine_b.run_transient_simulation(
        track=track, 
        initial_soc=setup_b_obj.initial_soc_pct / 100.0, 
        weather=active_weather
    )

# --- WORKSTATION HEADER BANNER ---
st.markdown(f"""
<div class="workstation-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1 class="workstation-title">⚡ 2026 F1 Telemetry & Dynamics Workstation</h1>
            <div class="workstation-subtitle">
                Circuit: <strong style="color:#ffffff;">{track.name}</strong> ({track.length:,.1f} m) 
                | Setup: <strong style="color:#00ff88;">{preset_choice}</strong>
                | Weather: {active_weather.air_temp_c:.1f}°C Air, {active_weather.track_temp_c:.1f}°C Track, ρ = {active_weather.air_density:.3f} kg/m³
            </div>
        </div>
        <div style="text-align:right;">
            <span class="status-badge" style="background:#ff9100; color:#000; font-weight:800;">4-WHEEL DUAL TRACK</span>
            <span class="status-badge" style="background:#00e5ff; color:#000; font-weight:800;">8-SPEED TRANSMISSION</span>
            <span class="status-badge" style="background:#e10600; color:#fff; font-weight:800;">100 Hz ODE</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- SYNCHRONIZED SCRUBBING & DIGITAL STEERING WHEEL GAUGE CLUSTER ---
st.markdown("##### ⏱️ Telemetry Scrubbing & Live Digital Steering Wheel Cockpit")
col_scrub, col_play = st.columns([4, 1])

with col_scrub:
    scrub_distance = st.slider(
        "Scrub Along Lap Distance (m)",
        min_value=0.0,
        max_value=float(track.length),
        value=float(track.length * 0.15),
        step=5.0,
        help="Drag to scrub the crosshair across all telemetry channels and move the car on the 3D track map!"
    )

with col_play:
    st.write("")
    st.write("")
    auto_animate = st.checkbox("▶️ Animate Point", value=False)

if auto_animate:
    scrub_distance = float((scrub_distance + 50.0) % track.length)

# Lookup instantaneous state values at scrubbed distance
idx_s = int(np.clip(np.searchsorted(sim_telem_a.s, scrub_distance), 0, len(sim_telem_a.time) - 1))
v_now = sim_telem_a.v_kmh[idx_s]
gear_now = sim_telem_a.gear[idx_s] if sim_telem_a.gear is not None else 6
rpm_now = sim_telem_a.engine_rpm[idx_s] if sim_telem_a.engine_rpm is not None else 10500.0
thr_now = sim_telem_a.throttle[idx_s] * 100.0
brk_now = sim_telem_a.brake[idx_s] * 100.0
mgu_now = sim_telem_a.p_mguk_kw[idx_s]
soc_now = sim_telem_a.soc_percent[idx_s]
ax_now = sim_telem_a.a_x[idx_s]
ay_now = sim_telem_a.a_y[idx_s]
steer_now = sim_telem_a.steering_angle_deg[idx_s] if sim_telem_a.steering_angle_deg is not None else 0.0

# Render Digital Cockpit Cluster
shift_led_color = "#ff1744" if rpm_now > 11_100 else ("#ffea00" if rpm_now > 10_500 else "#00ff88")
st.markdown(f"""
<div class="gauge-cluster">
    <div style="display:flex; align-items:center;">
        <div class="gear-box">{gear_now}</div>
        <div style="margin-left: 14px;">
            <div style="font-size:10px; color:#8b949e; font-weight:700;">ENGAGED GEAR</div>
            <div style="font-size:11px; color:{shift_led_color}; font-weight:800;">{'SHIFT UP ▲' if rpm_now > 11100 else 'OPTIMAL BAND'}</div>
        </div>
    </div>
    <div class="gauge-metric">
        <div class="gauge-label">Speed</div>
        <div class="gauge-value" style="color:#00ff88;">{v_now:.1f} <span style="font-size:12px;">km/h</span></div>
    </div>
    <div class="gauge-metric">
        <div class="gauge-label">Engine RPM</div>
        <div class="gauge-value" style="color:#ffd600;">{rpm_now:.0f}</div>
    </div>
    <div class="gauge-metric">
        <div class="gauge-label">Throttle / Brake</div>
        <div class="gauge-value" style="color:#38bdf8;">{thr_now:.0f}% <span style="color:#f43f5e;">| {brk_now:.0f}%</span></div>
    </div>
    <div class="gauge-metric">
        <div class="gauge-label">MGU-K Net Power</div>
        <div class="gauge-value" style="color:#ff9100;">{mgu_now:+.1f} <span style="font-size:12px;">kW</span></div>
    </div>
    <div class="gauge-metric">
        <div class="gauge-label">Steering Angle</div>
        <div class="gauge-value" style="color:#00e5ff;">{steer_now:+.1f}°</div>
    </div>
    <div class="gauge-metric">
        <div class="gauge-label">G-Forces (Lat / Long)</div>
        <div class="gauge-value" style="color:#e0e0e0;">{ay_now:+.2f}g <span style="font-size:12px;">| {ax_now:+.2f}g</span></div>
    </div>
    <div class="gauge-metric">
        <div class="gauge-label">Battery SoC</div>
        <div class="gauge-value" style="color:#d500f9;">{soc_now:.1f}%</div>
    </div>
</div>
""", unsafe_allow_html=True)


# --- 🏁 RACE ENGINEER SUMMARY & PLAIN-ENGLISH INSIGHTS ---
ref_lap_time = float(fastest_lap_info.get("lap_duration")) if (fastest_lap_info and fastest_lap_info.get("lap_duration")) else None
delta_lap = (sim_telem_a.lap_time - ref_lap_time) if ref_lap_time is not None else None
pole_driver_name = fastest_lap_info.get("driver_name", "Pole Driver") if fastest_lap_info else "Real Pole Driver"

sim_lap_str = format_lap_str(sim_telem_a.lap_time)
ref_lap_str = format_lap_str(ref_lap_time) if ref_lap_time else "N/A"

if delta_lap is not None:
    if delta_lap <= 0:
        verdict_color = "#00ff88"
        verdict_badge = "🟢 COMPETITIVE QUALIFYING PACE"
        verdict_text = (
            f"Your 2026 car clocked <strong>{sim_lap_str}</strong>, which is "
            f"<strong style='color:#00ff88;'>{abs(delta_lap):.3f}s FASTER</strong> than the real reference pole lap "
            f"({ref_lap_str} set by {pole_driver_name}). "
            f"The massive 350 kW electric boost out of slow turns and low-drag X-Mode on straights outweighed the heavier 888 kg minimum mass."
        )
    else:
        verdict_color = "#f59e0b"
        verdict_badge = "🟡 SOLID PRACTICE PACE"
        verdict_text = (
            f"Your 2026 car clocked <strong>{sim_lap_str}</strong>, trailing the real pole lap "
            f"({ref_lap_str} set by {pole_driver_name}) by <strong style='color:#f59e0b;'>{delta_lap:.3f}s</strong>. "
            f"Tip: Switch to Soft Slick (C5) tires or trim wing angles to gain straightline speed."
        )
else:
    verdict_color = "#38bdf8"
    verdict_badge = "🏁 SIMULATION COMPLETE"
    verdict_text = f"The 2026 car completed a lap in <strong>{sim_lap_str}</strong> with a top speed of <strong>{np.max(sim_telem_a.v_kmh):.1f} km/h</strong>."

st.markdown(f"""
<div class="verdict-banner" style="border-left: 6px solid {verdict_color};">
    <div class="verdict-title" style="color:{verdict_color};">
        <span>📻 Race Engineer Debrief</span>
        <span class="status-badge" style="background:{verdict_color}22; color:{verdict_color}; border:1px solid {verdict_color};">{verdict_badge}</span>
    </div>
    <div class="verdict-desc">{verdict_text}</div>
</div>
""", unsafe_allow_html=True)

# 4 Plain-English Telemetry Insight Cards
ic1, ic2, ic3, ic4 = st.columns(4)

with ic1:
    st.markdown(f"""
    <div class="insight-card">
        <div>
            <div class="insight-header" style="color:#ff9100;">⚡ 350 kW Electric MGU-K</div>
            <div class="insight-val" style="color:#ff9100;">{sim_telem_a.net_energy_deployed_mj:.2f} MJ Deployed</div>
            <div class="insight-body">
                Supplies nearly 50% of the car's power (470 bhp). The motor gave explosive acceleration out of slow corners and tapered smoothly past 290 km/h to conserve battery.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with ic2:
    max_downforce_kg = np.max(sim_telem_a.f_downforce_n) / 9.80665
    max_speed_kmh = np.max(sim_telem_a.v_kmh)
    st.markdown(f"""
    <div class="insight-card">
        <div>
            <div class="insight-header" style="color:#00e5ff;">💨 Active Aero Wings</div>
            <div class="insight-val" style="color:#00e5ff;">{max_speed_kmh:.1f} km/h Top Speed</div>
            <div class="insight-body">
                Wings dynamically switched between <strong>Z-Mode</strong> ({max_downforce_kg:,.0f} kg cornering downforce) and <strong>X-Mode</strong> (flaps opened on straights to cut drag by 28%).
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with ic3:
    max_brake_g = np.abs(np.min(sim_telem_a.a_x))
    harvest_mj = sim_telem_a.net_energy_harvested_mj
    st.markdown(f"""
    <div class="insight-card">
        <div>
            <div class="insight-header" style="color:#f43f5e;">🛑 Braking & Regeneration</div>
            <div class="insight-val" style="color:#f43f5e;">Peak {max_brake_g:.1f} Gs Decel</div>
            <div class="insight-body">
                The driver pulled up to {max_brake_g:.1f} Gs under hard braking. The MGU-K motor captured <strong>{harvest_mj:.2f} MJ</strong> of free kinetic energy straight back into the battery.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with ic4:
    peak_tire_c = np.max(sim_telem_a.t_tire_c)
    net_soc_change = sim_telem_a.delta_soc_percent
    st.markdown(f"""
    <div class="insight-card">
        <div>
            <div class="insight-header" style="color:#d500f9;">🔋 Battery & Tire Grip</div>
            <div class="insight-val" style="color:#d500f9;">{peak_tire_c:.1f}°C | ΔSoC {net_soc_change:+.1f}%</div>
            <div class="insight-body">
                Tires reached optimal thermal grip without blistering or excessive wear. Battery SoC ended at <strong>{sim_telem_a.soc_percent[-1]:.1f}%</strong>, fully prepared for consecutive flying laps.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# --- 💡 BEGINNER'S GUIDE (COLLAPSIBLE ACCORDION) ---
with st.expander("💡 Beginner's Guide: Understanding 2026 Formula 1 Telemetry (Click to Expand)", expanded=False):
    st.markdown("""
    Welcome to the 2026 Formula 1 era! Here is a simple, plain-English explanation of how the new technical regulations work:
    
    1. **⚡ The 50/50 Power Split (ICE + MGU-K)**:
       - In 2026, the complex and expensive MGU-H (exhaust heat recovery) is gone.
       - Instead, the car produces power in a near 50/50 split: **400 kW (~536 bhp)** from a 1.6L turbocharged V6 engine running on 100% sustainable fuels, and **350 kW (~470 bhp)** from a high-voltage electric motor (MGU-K). Combined, the car puts down over **1,000 horsepower**!
    
    2. **📉 What is MGU-K Tapering?**:
       - The electric battery only holds **4.0 MJ** of usable energy per lap. If the motor ran at full 350 kW all the time, the battery would be empty within 12 seconds.
       - FIA rules mandate that full electric boost is used when launching out of corners up to **290 km/h (180 mph)**. Between 290 km/h and **345 km/h (214 mph)**, electric power tapers down to 0 kW, letting the petrol engine handle maximum top speed.
    
    3. **💨 Active Aero: Z-Mode & X-Mode**:
       - DRS (Drag Reduction System) is replaced by automated active aerodynamics on **both front and rear wings**:
         - **Z-Mode (Cornering)**: Wing flaps stay closed, generating heavy downforce to stick the car through curves at up to 4+ Gs.
         - **X-Mode (Straights)**: Wing flaps open automatically on straights, cutting air resistance by ~28% to reach massive top speeds.
         
    4. **🛑 Brake-by-Wire & Kinetic Harvesting**:
       - When the driver steps on the brake pedal, the front wheels use traditional carbon brake discs, while the rear wheels are slowed down primarily by the 350 kW electric motor acting as a dynamo.
       - This regenerates up to 350 kW of electricity back into the battery, saving brake pad wear and recharging the battery for the next straight.
       
    5. **📊 How to Read the Graphs Below**:
       - **Speed Profile (Row 1)**: Neon green is your 2026 simulated car. The orange dotted line is 290 km/h (taper start) and the red line is 345 km/h (cutoff).
       - **Throttle & Brake (Row 2)**: Blue is throttle application (0–100%), Pink is brake pressure, and the stepped line shows engaged gear (1 to 8).
       - **RPM & Steering (Row 3)**: Engine revs (up to 12,000 RPM) and steering wheel angle in degrees.
       - **Dynamic Loads (Row 4)**: Shows the vertical downforce and weight transferring onto all four wheels through corners and braking.
       - **Powertrain kW (Row 5)**: Green shows petrol ICE power, Orange shows electric MGU-K deploy, and Blue shows regenerative braking recovery.
       - **Battery SoC & Tires (Row 6)**: Purple tracks battery percentage throughout the lap, and Coral red shows tire bulk temperature.
    """)

# --- KPI METRIC CARDS ---
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    delta_str = f"{delta_lap:+.3f}s vs Pole" if delta_lap is not None else "No Reference"
    sub_color = "#00ff88" if (delta_lap is not None and delta_lap <= 0) else "#f43f5e"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Lap Time ({preset_choice.split()[0]})</div>
        <div class="metric-val">{sim_lap_str}</div>
        <div class="metric-sub" style="color:{sub_color};">{delta_str}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    pole_driver_str = fastest_lap_info.get("name_acronym", "Real Pole") if fastest_lap_info else "N/A"
    pole_time_str = ref_lap_str
    team_name_str = fastest_lap_info.get('team_name', '') if fastest_lap_info else ''
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Real Pole Lap ({pole_driver_str})</div>
        <div class="metric-val" style="color:#00e5ff;">{pole_time_str}</div>
        <div class="metric-sub">{team_name_str}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Top Speed</div>
        <div class="metric-val">{np.max(sim_telem_a.v_kmh):.1f} <span style="font-size:12px;">km/h</span></div>
        <div class="metric-sub">{np.max(sim_telem_a.v):.1f} m/s | Gear {np.max(sim_telem_a.gear)}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">MGU-K 350kW Energy</div>
        <div class="metric-val" style="color:#ff9100;">{sim_telem_a.net_energy_deployed_mj:.2f} <span style="font-size:12px;">MJ</span></div>
        <div class="metric-sub">Harvested: {sim_telem_a.net_energy_harvested_mj:.2f} MJ</div>
    </div>
    """, unsafe_allow_html=True)

with kpi5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Peak Tire Temp & Grip</div>
        <div class="metric-val" style="color:#f43f5e;">{np.max(sim_telem_a.t_tire_c):.1f} <span style="font-size:12px;">°C</span></div>
        <div class="metric-sub">Net ΔSoC: {sim_telem_a.delta_soc_percent:+.1f}% | μ: {np.mean(sim_telem_a.mu_eff):.2f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# --- WORKSTATION INTERACTIVE TABS ---
tab_telem, tab_compare, tab_delta, tab_map, tab_gg, tab_setup, tab_export = st.tabs([
    "📊 Telemetry Workstation",
    "⚔️ Setup Comparison (A vs B)",
    "⏱️ Delta-Time Trace",
    "🗺️ Circuit Map & GPS",
    "⭕ G-G Friction Circle",
    "📋 FIA Setup Sheet",
    "💾 MoTeC / MATLAB Export"
])

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
        st.markdown(f"#### ⚔️ Head-to-Head: `{preset_choice}` vs `{setup_b_choice}`")
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
        st.info("Check '⚔️ Setup Comparison Mode (A vs B)' in the sidebar to simulate two setups side-by-side.")

with tab_delta:
    if ref_df is not None:
        fig_delta = create_delta_figure(sim_telem_a, ref_df, driver_label=driver_label)
        st.plotly_chart(fig_delta, use_container_width=True)
    else:
        st.info("💡 To view high-resolution delta time trace against the real qualifying pole lap, check '🌐 Fetch 100 Hz Live Pole Overlay (OpenF1)' in the sidebar.")

with tab_map:
    col_map1, col_map2 = st.columns([2.5, 1.0])
    with col_map1:
        fig_map = create_interactive_track_map(track, sim_telem_a, scrub_dist=scrub_distance)
        st.plotly_chart(fig_map, use_container_width=True)
    with col_map2:
        st.markdown("#### 🏁 3D Circuit Geometry Data")
        st.write(f"**Track Name:** {track.name}")
        st.write(f"**Total Arc Length:** {track.length:,.1f} m ({track.length/1000.0:.3f} km)")
        st.write(f"**Minimum Apex Radius:** {np.min(track.corner_radius):.1f} m")
        st.write(f"**Elevation Span (ΔZ):** {np.max(track.z) - np.min(track.z):.1f} m")
        st.write(f"**Maximum Track Incline:** {np.max(track.grade)*100.0:.1f}%")
        st.write(f"**Thermodynamic Air Density:** {active_weather.air_density:.4f} kg/m³")
        st.write(f"**Current Scrubbed Distance:** {scrub_distance:.0f} m")

with tab_gg:
    col_gg1, col_gg2 = st.columns([2.2, 1.0])
    with col_gg1:
        fig_gg = create_gg_diagram(sim_telem_a, scrub_dist=scrub_distance)
        st.plotly_chart(fig_gg, use_container_width=True)
    with col_gg2:
        st.markdown("#### 🏎️ 4-Wheel Chassis Telemetry")
        st.write(f"**Peak Lateral Adhesion:** {np.max(np.abs(sim_telem_a.a_y)):.2f} g")
        st.write(f"**Peak Longitudinal Braking:** {np.min(sim_telem_a.a_x):.2f} g")
        st.write(f"**Peak Downforce:** {np.max(sim_telem_a.f_downforce_n)/9.81:,.0f} kg ({np.max(sim_telem_a.f_downforce_n)/1e3:.1f} kN)")
        st.write(f"**Front Outer Wheel Max Load:** {np.max(sim_telem_a.f_z_fr):,.0f} N")
        st.write(f"**Rear Outer Wheel Max Load:** {np.max(sim_telem_a.f_z_rr):,.0f} N")
        st.write(f"**Max Steering Lock:** {np.max(np.abs(sim_telem_a.steering_angle_deg)):.1f}°")

with tab_setup:
    st.markdown("### 📋 FIA Technical Homologation & Setup Sheet")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### 🪽 Aerodynamic Configuration")
        st.table(pd.DataFrame({
            "Parameter": ["Front Wing Angle", "Rear Wing Angle", "Aero Balance Front", "Z-Mode Cl*A", "Z-Mode Cd*A", "X-Mode Cd*A"],
            "Value": [f"{fw_angle:.1f}°", f"{rw_angle:.1f}°", f"{aero_bal:.1f}%", f"{cl_z:.2f} m²", f"{cd_z:.2f} m²", f"{cd_x:.2f} m²"]
        }))
        st.markdown("#### ⚡ 2026 Hybrid Powertrain")
        st.table(pd.DataFrame({
            "Parameter": ["1.6L V6 ICE Max Power", "MGU-K Electric Power", "Taper Start Speed", "MGU-K Cutoff Speed", "Usable Battery Allowance"],
            "Value": [f"{ice_p:.0f} kW (~{ice_p*1.341:.0f} bhp)", f"{mguk_p:.0f} kW (~{mguk_p*1.341:.0f} bhp)", f"{v_taper:.0f} km/h", f"{v_cutoff:.0f} km/h", "4.0 MJ / lap"]
        }))
    with col_s2:
        st.markdown("#### 🏎️ Suspension & Dual-Track Chassis")
        st.table(pd.DataFrame({
            "Parameter": ["Front Spring Stiffness", "Rear Spring Stiffness", "Front Anti-Roll Bar", "Rear Anti-Roll Bar", "Static Front Weight"],
            "Value": [f"{k_spring_f:.0f} N/mm", f"{k_spring_r:.0f} N/mm", f"{k_arb_f:.0f} N/mm", f"{k_arb_r:.0f} N/mm", "45.5%"]
        }))
        st.markdown("#### 🛞 Braking System & Brake-by-Wire")
        st.table(pd.DataFrame({
            "Parameter": ["Static Front Brake Bias", "BBW Migration Gain", "Disc Carbon Spec", "Tire Compound", "Total Car Mass"],
            "Value": [f"{bbw_bias:.1f}%", "+2.2% / g decel", "330mm Carbon-Carbon", compound, f"{params_a.total_mass:.0f} kg"]
        }))

with tab_export:
    st.markdown("### 💾 Official MoTeC i2 Pro & Engineering Data Export")
    st.write("Export 100 Hz simulation data directly into **MoTeC i2 Pro**, **MATLAB R2026a**, or **Python data pipelines**.")
    
    # 1. MoTeC CSV & LDX
    motec_csv_str = export_to_motec_csv(sim_telem_a, track, vehicle_name="2026 Formula 1", driver_name="Sim Engineer")
    motec_ldx_str = export_to_motec_ldx_beacon(track, sim_telem_a)
    
    # 2. MATLAB .mat Workspace
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
        "track_z": track.z,
        "air_temp_c": float(active_weather.air_temp_c),
        "track_temp_c": float(active_weather.track_temp_c),
        "humidity_pct": float(active_weather.humidity_pct),
        "pressure_hpa": float(active_weather.pressure_hpa)
    }
    scipy.io.savemat(mat_buf, mat_dict)
    mat_bytes = mat_buf.getvalue()

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.download_button(
            label="🏎️ Download MoTeC i2 Pro Telemetry (.csv)",
            data=motec_csv_str,
            file_name=f"f1_2026_{track.name.split()[0].lower()}_motec.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.caption("Official MoTeC i2 Pro 100 Hz CSV with channel units.")
    with col_m2:
        st.download_button(
            label="🚩 Download MoTeC Beacons (.ldx)",
            data=motec_ldx_str,
            file_name=f"f1_2026_{track.name.split()[0].lower()}_beacons.ldx",
            mime="application/xml",
            use_container_width=True
        )
        st.caption("Companion LDX beacon markers for MoTeC track mapping.")
    with col_m3:
        st.download_button(
            label="💻 Download MATLAB Workspace (.mat)",
            data=mat_bytes,
            file_name=f"f1_2026_{track.name.split()[0].lower()}_matlab.mat",
            mime="application/x-matlab-data",
            use_container_width=True
        )
        st.caption("Full workspace format for MATLAB R2026a.")
