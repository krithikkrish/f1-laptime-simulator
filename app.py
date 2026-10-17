"""
Formula 1 2026 Transient Lap-Time & Hybrid Energy Deployment Simulator.
Accessible, Decongested, and Understandable for Everyone (Fans to Race Engineers).

Features:
- Dual Modes:
  1. 🟢 Simple & Clean Mode (Default): Spacious, easy-to-understand cards, plain English, single speed graph, interactive track map with moving car.
  2. ⚙️ Pro Engineering Mode: Individual modular telemetry charts with separate legends, G-G friction circle, setup sheet, and MATLAB exports.
- All 24 FIA Grand Prix Calendar Circuits pre-cached with authentic 3D waypoints & real weather.
- Authentic 2025 Saturday Qualifying (Q3) Pole Lap overlay from genuine telemetry.
- 100% physically solved at 100 Hz Forward-Euler ODE resolution on every user input change.
"""

import os
import io
import time
import json
import textwrap
import numpy as np
import pandas as pd
import scipy.io
import plotly.graph_objects as go
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
from f1_sim.pole_telemetry import (
    get_real_pole_telemetry,
    get_pole_benchmark_info
)
from f1_sim.interactive_plots import (
    create_individual_speed_figure,
    create_individual_inputs_figure,
    create_individual_powertrain_figure,
    create_individual_energy_tires_figure,
    create_individual_chassis_figure,
    create_interactive_track_map,
    create_gg_diagram,
    create_telemetry_figure
)

# Page configuration
st.set_page_config(
    page_title="F1 2026 Lap Simulator",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, Decongested, Premium Dark Glassmorphism Styling
st.markdown(textwrap.dedent("""
<style>
    /* Dark smooth workstation background */
    .stApp {
        background: radial-gradient(circle at 10% 10%, #0d1118 0%, #05080c 100%);
        color: #f0f6fc;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* Hero Verdict Card (Big, Clear, Decongested) */
    .hero-verdict-card {
        background: #111722;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 22px 26px;
        margin-bottom: 20px;
        box-shadow: 0 6px 25px rgba(0,0,0,0.4);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .hero-laptime {
        font-size: 46px;
        font-weight: 900;
        color: #00ff88;
        font-family: monospace;
        line-height: 1;
    }
    .hero-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 800;
        margin-top: 8px;
    }
    .hero-text {
        font-size: 14px;
        color: #d1d5db;
        max-width: 580px;
        line-height: 1.5;
        text-align: right;
    }
    
    /* 4 Big Decongested Stat Cards */
    .stat-card {
        background: #111722;
        border: 1px solid #21262d;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.25);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .stat-title {
        font-size: 12px;
        font-weight: 800;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .stat-val {
        font-size: 26px;
        font-weight: 900;
        margin-top: 6px;
        font-family: monospace;
    }
    .stat-desc {
        font-size: 12px;
        color: #9ca3af;
        margin-top: 6px;
        line-height: 1.4;
    }
</style>
""").strip(), unsafe_allow_html=True)


@st.cache_resource
def get_client() -> OpenF1Client:
    return OpenF1Client()


# Country flag emoji dictionary for all 24 calendar venues
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


# ==========================================
# SIDEBAR: TRACK SELECTION & ADVANCED TUNING
# ==========================================
with st.sidebar:
    st.markdown("### 🏁 Grand Prix Venue")
    
    circuits_data = get_available_circuits_list()
    circ_options = [c["key"] for c in circuits_data]
    circ_labels = {c["key"]: c["label"] for c in circuits_data}
    
    # Default to Miami or Monza
    default_idx = 5 if len(circ_options) > 5 else 0
    selected_circuit = st.selectbox(
        "Choose Track",
        circ_options,
        index=default_idx,
        format_func=lambda k: circ_labels.get(k, k),
        help="Choose from all 24 Grand Prix circuits on the FIA Formula 1 World Championship calendar."
    )
    
    track, active_weather, track_meta = create_calendar_track(selected_circuit, ds=1.0)
    
    # Load authentic real-world 2025 qualifying pole lap telemetry
    pole_info = get_pole_benchmark_info(track_meta)
    ref_df = get_real_pole_telemetry(track_meta.get("meeting_key"), track.length)
    
    st.info(f"🏁 **2025 Benchmark:** {track_meta.get('country')} GP  \n"
            f"**Driver:** {pole_info['driver_name']} ({pole_info['team_name']})  \n"
            f"**Pole Lap:** `{pole_info['lap_time_str']}` (Official Q3)")

    st.markdown("---")
    
    # Collapsible Advanced Tuning (for race engineers only)
    with st.expander("🛠️ Advanced Engineering Sliders (Optional)", expanded=False):
        st.caption("Defaulted to official 2026 FIA technical regulations.")
        ice_p_override = st.slider("ICE Petrol Engine (kW)", 350.0, 430.0, 400.0, 5.0)
        mguk_p_override = st.slider("Electric MGU-K Motor (kW)", 250.0, 360.0, 350.0, 5.0)
        v_taper_override = st.slider("Electric Taper Speed (km/h)", 270.0, 310.0, 290.0, 5.0)
        v_cutoff_override = st.slider("Electric Cutoff Speed (km/h)", 320.0, 360.0, 345.0, 5.0)
        cl_z_override = st.slider("Corner Downforce (Cl*A)", 2.5, 4.5, 3.60, 0.1)
        cd_x_override = st.slider("Straight Drag (Cd*A)", 0.6, 1.3, 0.88, 0.05)
        bbw_bias_override = st.slider("Brake Balance (% Front)", 52.0, 60.0, 56.5, 0.5)
        soc_init_override = st.slider("Starting Battery (%)", 20.0, 100.0, 100.0, 5.0)
        use_adv = st.checkbox("Apply Advanced Sliders", value=False)


# ==========================================
# TOP HEADER BAR & DISPLAY MODE SWITCHER
# ==========================================
flag = COUNTRY_FLAGS.get(track_meta.get("country", ""), "🏁")

col_hdr1, col_hdr2 = st.columns([3.2, 1.8])
with col_hdr1:
    st.markdown(f"## {flag} {track.name.upper()}")
    st.caption(f"🏁 **Benchmark Comparison:** {pole_info['full_label']} (Official 2025 Q3 Pole) | Track Length: **{track.length:,.0f} m**")

with col_hdr2:
    view_mode = st.radio(
        "Display Mode",
        ["🟢 Simple & Clean (For Everyone)", "⚙️ Pro Engineering Telemetry"],
        index=0,
        horizontal=True
    )

# ==========================================
# 🎮 USER-FRIENDLY ONE-CLICK BUTTONS
# ==========================================
with st.container(border=True):
    col_b1, col_b2, col_b3 = st.columns([1.3, 1.1, 1.2])
    
    with col_b1:
        st.markdown("**🛞 Tire Compound**")
        tire_btn = st.pills(
            "Tire Compound",
            ["🔴 Soft (Fastest)", "🟡 Medium (Balanced)", "⚪ Hard (Durable)", "🔵 Wet (Rain)"],
            default="🔴 Soft (Fastest)",
            label_visibility="collapsed"
        )
        
    with col_b2:
        st.markdown("**⛽ Fuel Load**")
        fuel_btn = st.pills(
            "Fuel Load",
            ["⚡ Quali (Light, 25 kg)", "⏱️ Sprint (50 kg)", "🏁 Race Tank (100 kg)"],
            default="⚡ Quali (Light, 25 kg)",
            label_visibility="collapsed"
        )
        
    with col_b3:
        st.markdown("**🏎️ Car Setup**")
        setup_btn = st.pills(
            "Car Setup",
            ["⚖️ Balanced (Official)", "🚀 High Speed (Low Drag)", "🎯 High Grip (Corners)"],
            default="⚖️ Balanced (Official)",
            label_visibility="collapsed"
        )

# Map user-friendly buttons to physics parameters
if "High Speed" in (setup_btn or ""):
    current_setup = SETUP_PRESETS["monza"]
elif "High Grip" in (setup_btn or ""):
    current_setup = SETUP_PRESETS["monaco"]
elif "Wet" in (tire_btn or ""):
    current_setup = SETUP_PRESETS["wet"]
else:
    current_setup = SETUP_PRESETS["balanced"]

# Tire compound physics mapping
if "Medium" in (tire_btn or ""):
    compound = "Medium Slick"
    mu_val = 1.70
    is_wet = False
elif "Hard" in (tire_btn or ""):
    compound = "Hard Slick"
    mu_val = 1.62
    is_wet = False
elif "Wet" in (tire_btn or ""):
    compound = "Wet Treaded"
    mu_val = 1.25
    is_wet = True
else:
    compound = "Soft Slick"
    mu_val = 1.76
    is_wet = False

# Fuel load mapping
if "Race" in (fuel_btn or ""):
    fuel_m = 100.0
elif "Sprint" in (fuel_btn or ""):
    fuel_m = 50.0
else:
    fuel_m = 25.0

# Apply advanced slider overrides if checked
if 'use_adv' in locals() and use_adv:
    ice_p = ice_p_override
    mguk_p = mguk_p_override
    v_taper = v_taper_override
    v_cutoff = v_cutoff_override
    cl_z = cl_z_override
    cd_x = cd_x_override
    bbw_bias = bbw_bias_override
    soc_init = soc_init_override
else:
    ice_p = current_setup.p_ice_kw
    mguk_p = current_setup.p_mguk_kw
    v_taper = current_setup.v_taper_kmh
    v_cutoff = current_setup.v_cutoff_kmh
    cl_z = current_setup.cl_a_z_mode
    cd_x = current_setup.cd_a_x_mode
    bbw_bias = current_setup.brake_bias_front_pct
    soc_init = 100.0


# ==========================================
# SIMULATION SOLVER (100 Hz FORWARD EULER)
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
    cd_A_z_mode=current_setup.cd_a_z_mode,
    cl_A_x_mode=current_setup.cl_a_x_mode,
    cd_A_x_mode=cd_x,
    mu_peak=mu_val,
    tire_compound="WET" if is_wet else "SLICK"
)

engine_a = SimulationEngine(params=params_a, weather=active_weather)
engine_a.dual_track.aero_balance_f = current_setup.aero_balance_front_pct / 100.0
engine_a.dual_track.bbw_base_front_pct = bbw_bias / 100.0

t_start_ode = time.perf_counter()
sim_telem_a: LapTelemetry = engine_a.run_transient_simulation(
    track=track,
    initial_soc=soc_init / 100.0,
    weather=active_weather
)
ode_duration_ms = (time.perf_counter() - t_start_ode) * 1000.0

# Pole reference comparison
ref_lap_time = pole_info.get("lap_time_s")
delta_lap = (sim_telem_a.lap_time - ref_lap_time) if ref_lap_time is not None else None
sim_lap_str = format_lap_str(sim_telem_a.lap_time)
ref_lap_str = pole_info.get("lap_time_str", "N/A")



# ==========================================
# 🟢 MODE 1: SIMPLE & CLEAN (FOR EVERYONE)
# ==========================================
if "Simple" in view_mode:
    # 1. Hero Verdict Card (Big, Clear, Friendly)
    if delta_lap is not None:
        if delta_lap <= 0:
            v_badge_color = "#00ff88"
            v_badge_bg = "rgba(0, 255, 136, 0.15)"
            v_badge_title = f"🟢 {abs(delta_lap):.3f}s FASTER THAN 2025 POLE!"
            v_desc = (f"Great lap! Your 2026 car clocked <strong>{sim_lap_str}</strong>, beating the real 2025 pole lap "
                      f"({ref_lap_str} set by {pole_info['driver_name']} in the {pole_info['team_name']}) by "
                      f"<strong>{abs(delta_lap):.3f} seconds</strong> thanks to 350 kW instant electric boost and active aero!")
        else:
            v_badge_color = "#f59e0b"
            v_badge_bg = "rgba(245, 158, 11, 0.15)"
            v_badge_title = f"🟡 {delta_lap:.3f}s BEHIND 2025 POLE"
            v_desc = (f"Solid lap! Your 2026 car clocked <strong>{sim_lap_str}</strong>. You are trailing the 2025 pole lap "
                      f"({ref_lap_str} set by {pole_info['driver_name']}) by <strong>{delta_lap:.3f} seconds</strong>. "
                      f"Tip: Try switching to Soft Slick tires or lighter fuel in the sidebar.")
    else:
        v_badge_color = "#38bdf8"
        v_badge_bg = "rgba(56, 189, 248, 0.15)"
        v_badge_title = "🏁 SIMULATION COMPLETE"
        v_desc = f"Your 2026 car completed the lap in <strong>{sim_lap_str}</strong> with a top speed of <strong>{np.max(sim_telem_a.v_kmh):.1f} km/h</strong>."

    st.markdown(textwrap.dedent(f"""
    <div class="hero-verdict-card" style="border-left: 6px solid {v_badge_color};">
        <div>
            <div style="font-size:11px; font-weight:800; color:#8b949e; text-transform:uppercase; letter-spacing:1px;">2026 SIMULATED LAP TIME</div>
            <div class="hero-laptime">{sim_lap_str}</div>
            <div class="hero-badge" style="background:{v_badge_bg}; color:{v_badge_color}; border:1px solid {v_badge_color};">
                {v_badge_title}
            </div>
        </div>
        <div class="hero-text">
            {v_desc}
            <div style="margin-top:8px; font-size:11px; color:#8b949e; font-family:monospace;">
                ⚡ Solved at 100 Hz in {ode_duration_ms:.0f} ms | Benchmark: 2025 {track_meta.get('country')} GP (Q3)
            </div>
        </div>
    </div>
    """).strip(), unsafe_allow_html=True)

    # 2. Four Big Decongested Stat Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div>
                <div class="stat-title" style="color:#00ff88;">⏱️ LAP TIME</div>
                <div class="stat-val" style="color:#00ff88;">{sim_lap_str}</div>
                <div class="stat-desc">2025 Real Pole: <strong style="color:#ffffff;">{ref_lap_str}</strong><br>({pole_info['driver_name']} - {pole_info['team_name']})</div>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)
        
    with c2:
        top_kmh = np.max(sim_telem_a.v_kmh)
        top_mph = top_kmh * 0.621371
        ref_top = f"{ref_df['speed'].max():.0f} km/h" if (ref_df is not None and 'speed' in ref_df.columns) else "N/A"
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div>
                <div class="stat-title" style="color:#00e5ff;">🚀 TOP SPEED</div>
                <div class="stat-val" style="color:#00e5ff;">{top_kmh:.0f} <span style="font-size:14px;">km/h</span></div>
                <div class="stat-desc"><strong>{top_mph:.0f} mph</strong> reached on main straight.<br>(2025 Pole top speed: <strong style="color:#ffffff;">{ref_top}</strong>)</div>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)
        
    with c3:
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div>
                <div class="stat-title" style="color:#ff9100;">⚡ ELECTRIC BOOST</div>
                <div class="stat-val" style="color:#ff9100;">{params_a.p_mguk_deploy_max/1e3:.0f} kW</div>
                <div class="stat-desc">Delivered <strong>+470 horsepower</strong> of instant electric acceleration out of every turn.</div>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)
        
    with c4:
        st.markdown(textwrap.dedent(f"""
        <div class="stat-card">
            <div>
                <div class="stat-title" style="color:#d500f9;">🔋 BATTERY HEALTH</div>
                <div class="stat-val" style="color:#d500f9;">{sim_telem_a.soc_percent[-1]:.0f}% Left</div>
                <div class="stat-desc">Recharged <strong>{sim_telem_a.net_energy_harvested_mj:.2f} MJ</strong> of electricity during braking!</div>
            </div>
        </div>
        """).strip(), unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 3. Interactive Driving Experience (Track Map + Clean Cockpit)
    st.markdown("### 🏎️ Live Lap Visualizer")
    st.caption("Drag the slider to drive the car around the circuit and see live cockpit telemetry!")
    
    col_scrub1, col_scrub2 = st.columns([4, 1])
    with col_scrub1:
        scrub_m = st.slider(
            "Drive along track (meters)",
            min_value=0.0,
            max_value=float(track.length),
            value=float(track.length * 0.20),
            step=10.0,
            label_visibility="collapsed"
        )
    with col_scrub2:
        animate_live = st.checkbox("▶️ Drive / Animate", value=False)
        
    if animate_live:
        scrub_m = float((scrub_m + 60.0) % track.length)

    idx_now = int(np.clip(np.searchsorted(sim_telem_a.s, scrub_m), 0, len(sim_telem_a.time) - 1))
    cur_v_kmh = sim_telem_a.v_kmh[idx_now]
    cur_v_mph = cur_v_kmh * 0.621371
    cur_gear = sim_telem_a.gear[idx_now] if sim_telem_a.gear is not None else 7
    cur_thr = sim_telem_a.throttle[idx_now] * 100.0
    cur_brk = sim_telem_a.brake[idx_now] * 100.0
    cur_mgu = sim_telem_a.p_mguk_kw[idx_now]
    cur_aero = "Active Aero Open (Low Drag X-Mode)" if (sim_telem_a.aero_mode is not None and sim_telem_a.aero_mode[idx_now] == "X_MODE") else "High Downforce (Z-Mode)"

    col_track_view, col_dash_view = st.columns([1.6, 1.0], gap="medium")
    
    with col_track_view:
        fig_track = create_interactive_track_map(track, sim_telem_a, scrub_dist=scrub_m)
        st.plotly_chart(fig_track, use_container_width=True)
        
    with col_dash_view:
        # Native Streamlit Cockpit Container (Zero HTML markdown bug risk)
        with st.container(border=True):
            st.caption("🏎️ **LIVE COCKPIT TELEMETRY**")
            
            c_gauge1, c_gauge2 = st.columns([2, 1])
            with c_gauge1:
                st.metric(
                    label="SPEED", 
                    value=f"{cur_v_kmh:.0f} km/h", 
                    delta=f"{cur_v_mph:.0f} mph", 
                    delta_color="off"
                )
            with c_gauge2:
                st.metric(
                    label="GEAR", 
                    value=f"{cur_gear}"
                )
                
            st.progress(min(cur_thr / 100.0, 1.0), text=f"Gas Pedal: {cur_thr:.0f}%")
            st.progress(min(cur_brk / 100.0, 1.0), text=f"Brake Pedal: {cur_brk:.0f}%")
            
            st.divider()
            mgu_str = f"⚡ +{int(cur_mgu)} kW (Deploying)" if cur_mgu >= 0 else f"⚡ {int(cur_mgu)} kW (Regenerating)"
            st.markdown(f"**Motor:** `{mgu_str}`")
            st.markdown(f"**Aero:** `{cur_aero}`")
            st.caption(f"🛞 **Tires:** {compound} ({np.max(sim_telem_a.t_tire_c):.0f}°C)")

    # 4. Clean Speed Chart With Separate Legend & Authentic 2025 Pole Line
    st.markdown("### 📈 Speed Over the Lap")
    st.caption(f"Comparing your 2026 car against **{pole_info['driver_name']} ({pole_info['team_name']})'s real 2025 pole lap**. Notice where 2026 pulls ahead on straights!")
    fig_speed = create_individual_speed_figure(
        sim_telem=sim_telem_a,
        ref_df=ref_df,
        track=track,
        driver_label=f"2025 Pole: {pole_info['driver_name']} ({pole_info['team_name']})",
        scrub_dist=scrub_m
    )
    st.plotly_chart(fig_speed, use_container_width=True)

    # 5. Friendly Beginner's Guide (Collapsible)
    with st.expander("💡 How does a 2026 Formula 1 car work? (Click to Read Plain English Guide)", expanded=False):
        st.markdown("""
        In 2026, Formula 1 is introducing revolutionary technical regulations. Here is everything you need to know:
        
        1. **⚡ The 50/50 Power Engine**:
           - 2026 cars get half their power from petrol (**400 kW / 536 hp**) and half from electricity (**350 kW / 470 hp**)!
           - That's over **1,000 total horsepower**, giving explosive acceleration out of every turn.
        
        2. **📉 What is Electric Tapering?**:
           - Batteries cannot provide full power for an entire lap without running out in 15 seconds.
           - So the electric motor pushes at full 350 kW up to **290 km/h (180 mph)**, then automatically dials back so the petrol engine handles top speed without draining the battery.
        
        3. **💨 Active Aero Wings**:
           - DRS is replaced by automated wings!
           - In corners, the wings close (**Z-Mode**) to create massive downforce that glues the car to the tarmac.
           - On straights, flaps open (**X-Mode**) to slash aerodynamic drag by 28% and reach over **340 km/h**.
        
        4. **🛑 Free Electricity Under Braking**:
           - When you step on the brakes, the electric motor acts as a generator, harvesting up to 350 kW of kinetic energy to recharge the battery for the next straight.
        """)


# ==========================================
# ⚙️ MODE 2: PRO ENGINEERING TELEMETRY
# ==========================================
else:
    st.markdown("### 🛠️ Pro Motorsport Engineering Workstation")
    st.caption("Modular telemetry channels with individual legends, G-G friction circles, and vehicle dynamics data.")

    tab_telem_pro, tab_gg_pro, tab_setup_pro, tab_export_pro = st.tabs([
        "📊 Engineering Telemetry Channels",
        "⭕ G-G Friction Circle",
        "📋 FIA Homologation Setup Sheet",
        "💾 MoTeC / MATLAB / HTML Export"
    ])

    with tab_telem_pro:
        st.markdown("#### 1. Speed Profile & Lap Time Comparison")
        st.caption("Overlay of 2026 simulation speed vs authentic 2025 qualifying pole telemetry.")
        fig_pro_speed = create_individual_speed_figure(
            sim_telem=sim_telem_a,
            ref_df=ref_df,
            track=track,
            driver_label=f"2025 Pole: {pole_info['driver_name']} ({pole_info['team_name']})"
        )
        st.plotly_chart(fig_pro_speed, use_container_width=True)

        st.markdown("#### 2. Driver Inputs & Sequential Transmission")
        st.caption("Gas pedal %, brake pedal % with hydraulic line pressure, and 8-speed sequential gear shifts.")
        fig_pro_inputs = create_individual_inputs_figure(
            sim_telem=sim_telem_a,
            ref_df=ref_df,
            track=track
        )
        st.plotly_chart(fig_pro_inputs, use_container_width=True)

        st.markdown("#### 3. 2026 Hybrid Powertrain Deployment")
        st.caption("Internal combustion engine power (kW), 350 kW MGU-K corner acceleration boost, and regenerative braking.")
        fig_pro_pwr = create_individual_powertrain_figure(
            sim_telem=sim_telem_a,
            track=track
        )
        st.plotly_chart(fig_pro_pwr, use_container_width=True)

        st.markdown("#### 4. Battery Energy Storage & Tire Temperatures")
        st.caption("Battery state-of-charge (SoC %) across the lap and Pirelli bulk tire thermal window.")
        fig_pro_energy = create_individual_energy_tires_figure(
            sim_telem=sim_telem_a,
            track=track
        )
        st.plotly_chart(fig_pro_energy, use_container_width=True)

        st.markdown("#### 5. 4-Wheel Chassis Load Transfer & Aerodynamic Downforce")
        st.caption("Axle vertical loads (kg) accounting for longitudinal braking weight transfer and lateral cornering roll.")
        fig_pro_chassis = create_individual_chassis_figure(
            sim_telem=sim_telem_a,
            track=track
        )
        st.plotly_chart(fig_pro_chassis, use_container_width=True)

    with tab_gg_pro:
        col_g1, col_g2 = st.columns([2.2, 1.0])
        with col_g1:
            fig_gg_pro = create_gg_diagram(sim_telem_a)
            st.plotly_chart(fig_gg_pro, use_container_width=True)
        with col_g2:
            st.markdown("#### 🏎️ 4-Wheel Chassis Telemetry")
            st.write(f"**Peak Lateral Adhesion:** {np.max(np.abs(sim_telem_a.a_y)):.2f} g")
            st.write(f"**Peak Longitudinal Braking:** {np.min(sim_telem_a.a_x):.2f} g")
            st.write(f"**Peak Aerodynamic Downforce:** {np.max(sim_telem_a.f_downforce_n)/9.81:,.0f} kg")
            st.write(f"**Max Outer Wheel Load:** {max(np.max(sim_telem_a.f_z_fr), np.max(sim_telem_a.f_z_rr)):,.0f} N")
            st.write(f"**Dynamic BBW Migration:** {np.min(sim_telem_a.bbw_front_pct):.1f}% ➔ {np.max(sim_telem_a.bbw_front_pct):.1f}% Front")

    with tab_setup_pro:
        st.markdown("#### 📋 FIA Technical Homologation & Setup Sheet")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("**🪽 Aerodynamic Configuration**")
            st.table(pd.DataFrame({
                "Parameter": ["Aero Balance Front", "Z-Mode Cl*A", "X-Mode Cd*A"],
                "Value": [f"{current_setup.aero_balance_front_pct:.1f}%", f"{cl_z:.2f} m²", f"{cd_x:.2f} m²"]
            }))
            st.markdown("**⚡ 2026 Hybrid Powertrain**")
            st.table(pd.DataFrame({
                "Parameter": ["ICE Max Power", "MGU-K Electric Power", "Taper Threshold", "Cutoff Speed"],
                "Value": [f"{ice_p:.0f} kW", f"{mguk_p:.0f} kW", f"{v_taper:.0f} km/h", f"{v_cutoff:.0f} km/h"]
            }))
        with col_s2:
            st.markdown("**🏎️ Suspension & Chassis**")
            st.table(pd.DataFrame({
                "Parameter": ["Front Spring Rate", "Rear Spring Rate", "Front Weight Share"],
                "Value": [f"{current_setup.front_spring_rate_n_mm:.0f} N/mm", f"{current_setup.rear_spring_rate_n_mm:.0f} N/mm", "45.5%"]
            }))
            st.markdown("**🛞 Braking & Tires**")
            st.table(pd.DataFrame({
                "Parameter": ["Front Brake Bias", "Tire Compound", "Total Car Mass"],
                "Value": [f"{bbw_bias:.1f}%", compound, f"{params_a.total_mass:.0f} kg"]
            }))

    with tab_export_pro:
        st.markdown("#### 💾 Official Motorsport Telemetry Export")
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
            "p_ice_kw": sim_telem_a.p_ice_kw,
            "p_mguk_kw": sim_telem_a.p_mguk_kw,
            "soc_percent": sim_telem_a.soc_percent
        }
        scipy.io.savemat(mat_buf, mat_dict)
        mat_bytes = mat_buf.getvalue()

        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.download_button("🏎️ Download MoTeC i2 Pro CSV (.csv)", motec_csv_str, f"f1_2026_{track.name.split()[0].lower()}_motec.csv", "text/csv", use_container_width=True)
            st.download_button("🚩 Download MoTeC Beacons (.ldx)", motec_ldx_str, f"f1_2026_{track.name.split()[0].lower()}_beacons.ldx", "application/xml", use_container_width=True)
        with col_ex2:
            st.download_button("💻 Download MATLAB Workspace (.mat)", mat_bytes, f"f1_2026_{track.name.split()[0].lower()}_matlab.mat", "application/x-matlab-data", use_container_width=True)
            html_telem = fig_pro_speed.to_html(include_plotlyjs="cdn")
            st.download_button("🌐 Download Interactive HTML (.html)", html_telem, f"f1_2026_{track.name.split()[0].lower()}_interactive.html", "text/html", use_container_width=True)
