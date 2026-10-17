"""
Professional Motorsport Telemetry & Workstation Visualization Suite using Plotly.
Styled to the standard of McLaren Applied ATLAS & MoTeC i2 Pro:
1. Multi-channel synchronized telemetry (Speed, Throttle/Brake, Gear, RPM, 4-Wheel Loads, MGU-K kW, SoC, Tires)
2. Synchronized distance scrubbing cursor across all channels and 3D track map
3. Setup Comparison Mode (Setup A vs Setup B) with Delta-V and Delta-T traces
4. 2D/3D Circuit Map with dynamic car beacon marker
5. G-G Friction Circle envelope with instantaneous operating point
"""

import os
from typing import Optional, Dict, Any, List
import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .track import Track
from .lts_engine import LapTelemetry


# Professional McLaren ATLAS / MoTeC i2 color palette
COLOR_SIM = "#00ff88"       # Neon Green (2026 Sim Car / Setup A)
COLOR_REF = "#00e5ff"       # Cyan (Real Pole Driver / Setup B)
COLOR_MGU = "#ff9100"       # Neon Orange (MGU-K 350kW Deploy)
COLOR_REGEN = "#2979ff"     # Blue (MGU-K Regen)
COLOR_SOC = "#d500f9"       # Magenta (Battery SoC)
COLOR_TIRE = "#ff1744"      # Coral Red (Tire Temperature)
COLOR_SECTOR = "#616161"    # Gray (Timing Sectors)
COLOR_CURSOR = "#ffea00"    # Bright Yellow/Amber (Scrubbing Crosshair)


def create_telemetry_figure(
    sim_telem: LapTelemetry, 
    ref_df: Optional[pd.DataFrame] = None, 
    track: Optional[Track] = None,
    driver_label: str = "Real F1 Pole Lap",
    scrub_dist: Optional[float] = None,
    setup_b_telem: Optional[LapTelemetry] = None,
    setup_b_label: Optional[str] = None
) -> go.Figure:
    """
    Constructs an industrial-grade 6-channel race engineer telemetry dashboard:
    1. Speed Profile (km/h) + 290/345 km/h Taper Lines + Reference / Setup B Overlay
    2. Driver Inputs (Throttle & Brake %) & Engaged Gear (1-8)
    3. Engine RPM & Steering Angle (deg)
    4. 4-Corner Tire Vertical Normal Loads (FL, FR, RL, RR in N)
    5. 2026 Powertrain Deployment (kW) & Active Aero
    6. Battery Energy Storage (SoC %) & Tire Bulk Temperature (°C)
    """
    fig = make_subplots(
        rows=6, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        subplot_titles=(
            "Speed Profile (km/h) — 2026 Sim vs " + (setup_b_label if setup_b_telem else driver_label),
            "Driver Inputs: Throttle & Brake (%) | Gear (1-8)",
            "Engine RPM & Steering Wheel Angle (deg)",
            "4-Corner Dynamic Vertical Loads (FL, FR, RL, RR in N)",
            "2026 Powertrain: ICE kW & MGU-K Deploy/Harvest (kW)",
            "Battery SoC (%) & Tire Bulk Temperature (°C)"
        ),
        row_heights=[0.24, 0.15, 0.15, 0.16, 0.15, 0.15]
    )

    s_sim = sim_telem.s

    # 1. Speed Profile
    fig.add_trace(
        go.Scatter(
            x=s_sim, y=sim_telem.v_kmh,
            mode='lines', name='Setup A (2026 Sim)' if setup_b_telem else '2026 Simulation Car',
            line=dict(color=COLOR_SIM, width=2.2),
            hovertemplate="Distance: %{x:.1f} m<br>Sim Speed: %{y:.1f} km/h<extra></extra>"
        ),
        row=1, col=1
    )

    if setup_b_telem is not None:
        fig.add_trace(
            go.Scatter(
                x=setup_b_telem.s, y=setup_b_telem.v_kmh,
                mode='lines', name=setup_b_label or 'Setup B',
                line=dict(color=COLOR_REF, width=2.0, dash='dash'),
                hovertemplate="Setup B Speed: %{y:.1f} km/h<extra></extra>"
            ),
            row=1, col=1
        )
    elif ref_df is not None and "distance_m" in ref_df.columns and "speed" in ref_df.columns:
        fig.add_trace(
            go.Scatter(
                x=ref_df["distance_m"], y=ref_df["speed"],
                mode='lines', name=driver_label,
                line=dict(color=COLOR_REF, width=1.6, dash='dot'),
                hovertemplate="Ref Speed: %{y:.1f} km/h<extra></extra>"
            ),
            row=1, col=1
        )

    # 2026 Technical Regulation Taper Markers
    fig.add_hline(
        y=290.0, line=dict(color="#ffa726", width=1.0, dash="dash"),
        annotation_text="2026 MGU-K Taper (290 km/h)", annotation_position="top right",
        annotation_font=dict(size=8, color="#ffa726"),
        row=1, col=1
    )
    fig.add_hline(
        y=345.0, line=dict(color="#ef5350", width=1.0, dash="dash"),
        annotation_text="2026 MGU-K Cutoff (345 km/h)", annotation_position="top right",
        annotation_font=dict(size=8, color="#ef5350"),
        row=1, col=1
    )

    # 2. Driver Inputs & Gear
    fig.add_trace(
        go.Scatter(
            x=s_sim, y=sim_telem.throttle * 100.0,
            mode='lines', name='Throttle (%)',
            line=dict(color=COLOR_SIM, width=1.4),
            hovertemplate="Throttle: %{y:.1f}%<extra></extra>"
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=s_sim, y=sim_telem.brake * 100.0,
            mode='lines', name='Brake (%)',
            line=dict(color=COLOR_TIRE, width=1.4),
            fill='tozeroy', fillcolor='rgba(255, 23, 68, 0.20)',
            hovertemplate="Brake: %{y:.1f}%<extra></extra>"
        ),
        row=2, col=1
    )
    if sim_telem.gear is not None:
        fig.add_trace(
            go.Scatter(
                x=s_sim, y=sim_telem.gear * 12.0,  # Scale to 0-100% axis
                mode='lines', name='Gear (1-8)',
                line=dict(color="#e0e0e0", width=1.2, shape='hv'),
                hovertemplate="Gear: %{text}<extra></extra>",
                text=sim_telem.gear
            ),
            row=2, col=1
        )

    # 3. Engine RPM & Steering Angle
    if sim_telem.engine_rpm is not None:
        fig.add_trace(
            go.Scatter(
                x=s_sim, y=sim_telem.engine_rpm,
                mode='lines', name='Engine RPM',
                line=dict(color="#ffeb3b", width=1.5),
                hovertemplate="RPM: %{y:.0f}<extra></extra>"
            ),
            row=3, col=1
        )
    if sim_telem.steering_angle_deg is not None:
        fig.add_trace(
            go.Scatter(
                x=s_sim, y=sim_telem.steering_angle_deg * 200.0 + 8000.0,  # Scaled on RPM visual axis
                mode='lines', name='Steering Angle (scaled)',
                line=dict(color="#00e5ff", width=1.2),
                hovertemplate="Steer: %{text:.1f}°<extra></extra>",
                text=sim_telem.steering_angle_deg
            ),
            row=3, col=1
        )

    # 4. 4-Corner Tire Vertical Normal Loads (Load Transfer)
    if sim_telem.f_z_fl is not None:
        fig.add_trace(
            go.Scatter(
                x=s_sim, y=sim_telem.f_z_fl,
                mode='lines', name='Wheel Load FL (N)',
                line=dict(color="#00e5ff", width=1.3),
                hovertemplate="FL Load: %{y:.0f} N<extra></extra>"
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=s_sim, y=sim_telem.f_z_fr,
                mode='lines', name='Wheel Load FR (N)',
                line=dict(color="#2979ff", width=1.3, dash='dash'),
                hovertemplate="FR Load: %{y:.0f} N<extra></extra>"
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=s_sim, y=sim_telem.f_z_rl,
                mode='lines', name='Wheel Load RL (N)',
                line=dict(color="#ff9100", width=1.3),
                hovertemplate="RL Load: %{y:.0f} N<extra></extra>"
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=s_sim, y=sim_telem.f_z_rr,
                mode='lines', name='Wheel Load RR (N)',
                line=dict(color="#ff1744", width=1.3, dash='dash'),
                hovertemplate="RR Load: %{y:.0f} N<extra></extra>"
            ),
            row=4, col=1
        )

    # 5. 2026 Powertrain Deployment
    fig.add_trace(
        go.Scatter(
            x=s_sim, y=sim_telem.p_ice_kw,
            mode='lines', name='1.6L V6 ICE (kW)',
            line=dict(color="#ffd600", width=1.4),
            hovertemplate="ICE: %{y:.1f} kW<extra></extra>"
        ),
        row=5, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=s_sim, y=sim_telem.p_mguk_kw,
            mode='lines', name='2026 MGU-K (kW)',
            line=dict(color=COLOR_MGU, width=1.6),
            fill='tozeroy', fillcolor='rgba(255, 145, 0, 0.20)',
            hovertemplate="MGU-K: %{y:.1f} kW<extra></extra>"
        ),
        row=5, col=1
    )

    # 6. Battery SoC & Tire Temperatures
    fig.add_trace(
        go.Scatter(
            x=s_sim, y=sim_telem.soc_percent,
            mode='lines', name='Battery SoC (%)',
            line=dict(color=COLOR_SOC, width=1.8),
            fill='tozeroy', fillcolor='rgba(213, 0, 249, 0.12)',
            hovertemplate="Battery SoC: %{y:.2f}%<extra></extra>"
        ),
        row=6, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=s_sim, y=sim_telem.t_tire_c,
            mode='lines', name='Tire Temp (°C)',
            line=dict(color=COLOR_TIRE, width=1.6),
            hovertemplate="Tire: %{y:.1f} °C<extra></extra>"
        ),
        row=6, col=1
    )

    # Add sector markers across all subplots
    if track is not None and track.sectors:
        for sec_name, s_start, s_end in track.sectors:
            for r in range(1, 7):
                fig.add_vline(
                    x=s_end, line=dict(color=COLOR_SECTOR, width=1.0, dash="dash"),
                    row=r, col=1
                )
            fig.add_annotation(
                x=s_end - 60, y=70, text=sec_name, showarrow=False,
                font=dict(size=8, color="#9e9e9e"), textangle=-90,
                row=1, col=1
            )

    # Add interactive scrubbing cursor if specified
    if scrub_dist is not None:
        for r in range(1, 7):
            fig.add_vline(
                x=scrub_dist,
                line=dict(color=COLOR_CURSOR, width=2.0, dash="solid"),
                row=r, col=1
            )
        fig.add_annotation(
            x=scrub_dist, y=340, text=f"Scrub: {scrub_dist:.0f}m",
            showarrow=True, arrowhead=2, arrowcolor=COLOR_CURSOR,
            font=dict(size=10, color=COLOR_CURSOR),
            row=1, col=1
        )

    fig.update_layout(
        template="plotly_dark",
        height=1080,
        hovermode="x unified",
        margin=dict(l=60, r=40, t=45, b=40),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor="rgba(15, 23, 42, 0.8)", bordercolor="#334155", borderwidth=1,
            font=dict(size=10)
        ),
        paper_bgcolor="#090d16",
        plot_bgcolor="#111827"
    )

    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor="#1f2937", title_text="Track Distance (m)", row=6, col=1)
    for r in range(1, 6):
        fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor="#1f2937", row=r, col=1)

    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1, range=[35, 365], showgrid=True, gridcolor="#1f2937")
    fig.update_yaxes(title_text="Inputs (%)", row=2, col=1, range=[-5, 105], showgrid=True, gridcolor="#1f2937")
    fig.update_yaxes(title_text="Engine RPM", row=3, col=1, range=[3800, 12200], showgrid=True, gridcolor="#1f2937")
    fig.update_yaxes(title_text="Wheel Load (N)", row=4, col=1, range=[0, 12000], showgrid=True, gridcolor="#1f2937")
    fig.update_yaxes(title_text="Power (kW)", row=5, col=1, showgrid=True, gridcolor="#1f2937")
    fig.update_yaxes(title_text="SoC / Temp", row=6, col=1, showgrid=True, gridcolor="#1f2937")

    return fig


def create_setup_comparison_figure(
    telem_a: LapTelemetry,
    telem_b: LapTelemetry,
    label_a: str = "Setup A",
    label_b: str = "Setup B"
) -> go.Figure:
    """
    Renders an engineering A/B setup comparison dashboard:
    1. Speed profile overlay v_A(s) vs v_B(s)
    2. Delta-Time trace Delta_t(s) = t_B(s) - t_A(s)
    3. MGU-K Hybrid Power differential
    """
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=(
            f"Speed Profile: {label_a} vs {label_b}",
            f"Lap Delta Time: Delta_t(s) [Positive: {label_a} is faster]",
            "MGU-K Hybrid Deployment Differential (kW)"
        ),
        row_heights=[0.45, 0.30, 0.25]
    )

    s = telem_a.s
    # Interpolate Setup B onto common distance grid
    v_b_interp = np.interp(s, telem_b.s, telem_b.v_kmh)
    t_b_interp = np.interp(s, telem_b.s, telem_b.time)
    mgu_b_interp = np.interp(s, telem_b.s, telem_b.p_mguk_kw)

    delta_time = t_b_interp - telem_a.time

    # 1. Speed overlay
    fig.add_trace(
        go.Scatter(x=s, y=telem_a.v_kmh, mode='lines', name=label_a, line=dict(color=COLOR_SIM, width=2.0)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=s, y=v_b_interp, mode='lines', name=label_b, line=dict(color=COLOR_REF, width=2.0, dash='dash')),
        row=1, col=1
    )

    # 2. Delta Time
    fig.add_trace(
        go.Scatter(
            x=s, y=delta_time,
            mode='lines', name='Delta Time (s)',
            line=dict(color="#ffea00", width=2.0),
            fill='tozeroy', fillcolor='rgba(255, 234, 0, 0.15)',
            hovertemplate="Distance: %{x:.1f} m<br>Delta: %{y:+.3f} s<extra></extra>"
        ),
        row=2, col=1
    )
    fig.add_hline(y=0.0, line=dict(color="#ffffff", width=1.0, dash="dash"), row=2, col=1)

    # 3. MGU-K Power diff
    fig.add_trace(
        go.Scatter(x=s, y=telem_a.p_mguk_kw, mode='lines', name=f"{label_a} MGU-K", line=dict(color=COLOR_MGU, width=1.5)),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=s, y=mgu_b_interp, mode='lines', name=f"{label_b} MGU-K", line=dict(color="#2979ff", width=1.5, dash='dash')),
        row=3, col=1
    )

    fig.update_layout(
        template="plotly_dark",
        height=680,
        hovermode="x unified",
        margin=dict(l=60, r=40, t=50, b=40),
        paper_bgcolor="#090d16",
        plot_bgcolor="#111827"
    )
    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1, gridcolor="#1f2937")
    fig.update_yaxes(title_text="Delta Time (s)", row=2, col=1, gridcolor="#1f2937")
    fig.update_yaxes(title_text="MGU-K (kW)", row=3, col=1, gridcolor="#1f2937")

    return fig


def create_interactive_track_map(
    track: Track, 
    sim_telem: Optional[LapTelemetry] = None,
    scrub_dist: Optional[float] = None
) -> go.Figure:
    """
    Renders an interactive 2D circuit geometry map colored by simulated vehicle speed.
    Features hover tooltips with distance, speed, corner radius, elevation, and sector zones.
    If scrub_dist is passed, renders a glowing beacon marker at the car's exact position.
    """
    if sim_telem is not None:
        v_interp = np.interp(track.s, sim_telem.s, sim_telem.v_kmh)
    else:
        v_interp = np.ones_like(track.s) * 200.0

    fig = go.Figure()

    # Track center line colored by speed
    fig.add_trace(
        go.Scatter(
            x=track.x, y=track.y,
            mode='markers+lines',
            line=dict(width=5.0, color='#1f2937'),
            marker=dict(
                size=3.8,
                color=v_interp,
                colorscale="Turbo",
                colorbar=dict(title="Speed (km/h)", thickness=15, len=0.8),
                showscale=True
            ),
            text=[
                f"Distance: {s:.0f} m<br>Speed: {v:.1f} km/h<br>Radius: {r:.0f} m<br>Grade: {g*100:.1f}%<br>Elev: {z:.1f} m"
                for s, v, r, g, z in zip(track.s, v_interp, track.corner_radius, track.grade, track.z)
            ],
            hoverinfo="text",
            name="Circuit Path"
        )
    )

    # Start/Finish line marker
    fig.add_trace(
        go.Scatter(
            x=[track.x[0]], y=[track.y[0]],
            mode='markers+text',
            marker=dict(size=14, color="#00ff88", symbol="star"),
            text=["START / FINISH"],
            textposition="top right",
            textfont=dict(color="#00ff88", size=11, family="monospace"),
            name="Start/Finish"
        )
    )

    # Sector boundary markers
    for sec_name, s_start, s_end in track.sectors:
        idx = int(np.clip(np.searchsorted(track.s, s_end), 0, len(track.s) - 1))
        fig.add_trace(
            go.Scatter(
                x=[track.x[idx]], y=[track.y[idx]],
                mode='markers+text',
                marker=dict(size=9, color="#ffd600", symbol="diamond"),
                text=[sec_name],
                textposition="bottom center",
                textfont=dict(color="#ffd600", size=10),
                showlegend=False
            )
        )

    # Dynamic car location marker on track when scrubbed
    if scrub_dist is not None:
        idx_scrub = int(np.clip(np.searchsorted(track.s, scrub_dist), 0, len(track.s) - 1))
        x_car = track.x[idx_scrub]
        y_car = track.y[idx_scrub]
        v_car = v_interp[idx_scrub]
        gear_val = int(sim_telem.gear[int(np.clip(np.searchsorted(sim_telem.s, scrub_dist), 0, len(sim_telem.time)-1))]) if (sim_telem and sim_telem.gear is not None) else 6
        
        fig.add_trace(
            go.Scatter(
                x=[x_car], y=[y_car],
                mode='markers+text',
                marker=dict(size=18, color=COLOR_CURSOR, symbol="circle", line=dict(color="#ffffff", width=2.5)),
                text=[f"🏎️ {v_car:.0f} km/h (G{gear_val})"],
                textposition="top center",
                textfont=dict(color=COLOR_CURSOR, size=12, family="monospace"),
                name="Car Position"
            )
        )

    fig.update_layout(
        title=dict(text=f"Circuit Layout & Speed Telemetry — {track.name}", font=dict(color="#00ff88", size=14)),
        template="plotly_dark",
        height=580,
        xaxis=dict(showgrid=False, zeroline=False, visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="#090d16",
        plot_bgcolor="#111827"
    )

    return fig


def create_gg_diagram(sim_telem: LapTelemetry, scrub_dist: Optional[float] = None) -> go.Figure:
    """
    Constructs the interactive G-G acceleration friction ellipse diagram.
    Plots lateral acceleration a_y vs longitudinal acceleration a_x in g's.
    """
    fig = go.Figure()

    # Scatter points colored by speed
    fig.add_trace(
        go.Scatter(
            x=sim_telem.a_y, y=sim_telem.a_x,
            mode='markers',
            marker=dict(
                size=4.0,
                color=sim_telem.v_kmh,
                colorscale="Plasma",
                colorbar=dict(title="Speed (km/h)", thickness=12, len=0.8),
                opacity=0.75
            ),
            text=[f"Dist: {s:.0f}m<br>Speed: {v:.1f} km/h<br>Lat: {ay:.2f}g<br>Long: {ax:.2f}g" 
                  for s, v, ay, ax in zip(sim_telem.s, sim_telem.v_kmh, sim_telem.a_y, sim_telem.a_x)],
            hoverinfo="text",
            name="Operating Envelope"
        )
    )

    # Friction Ellipse reference rings (1g, 2g, 3g, 4g, 5g)
    theta = np.linspace(0, 2 * np.pi, 100)
    for g_val in [1.0, 2.0, 3.0, 4.0, 5.0]:
        fig.add_trace(
            go.Scatter(
                x=g_val * np.cos(theta), y=g_val * np.sin(theta),
                mode='lines',
                line=dict(color="#374151", width=1.0, dash="dot"),
                hoverinfo="skip",
                showlegend=False
            )
        )
        fig.add_annotation(
            x=0.0, y=g_val, text=f"{int(g_val)}g", showarrow=False,
            font=dict(size=8, color="#9ca3af")
        )

    # Active scrubbed operating point
    if scrub_dist is not None:
        idx_s = int(np.clip(np.searchsorted(sim_telem.s, scrub_dist), 0, len(sim_telem.time) - 1))
        ax_pt = sim_telem.a_x[idx_s]
        ay_pt = sim_telem.a_y[idx_s]
        fig.add_trace(
            go.Scatter(
                x=[ay_pt], y=[ax_pt],
                mode='markers+text',
                marker=dict(size=14, color=COLOR_CURSOR, symbol="cross", line=dict(color="#ffffff", width=2)),
                text=[f"Point: Lat {ay_pt:+.2f}g, Long {ax_pt:+.2f}g"],
                textposition="top center",
                textfont=dict(color=COLOR_CURSOR, size=11),
                name="Current Point"
            )
        )

    fig.update_layout(
        title=dict(text="G-G Acceleration Diagram (Friction Circle Validation)", font=dict(color="#00e5ff", size=13)),
        xaxis=dict(title="Lateral Acceleration a_y (g)", range=[-5.5, 5.5], zeroline=True, zerolinecolor="#4b5563", gridcolor="#1f2937"),
        yaxis=dict(title="Longitudinal Acceleration a_x (g)", range=[-5.5, 3.5], zeroline=True, zerolinecolor="#4b5563", gridcolor="#1f2937", scaleanchor="x", scaleratio=1),
        template="plotly_dark",
        height=480,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor="#090d16",
        plot_bgcolor="#111827"
    )

    return fig


def create_delta_figure(sim_telem: LapTelemetry, ref_df: pd.DataFrame, driver_label: str = "Real F1 Pole Lap") -> go.Figure:
    """
    Constructs the real-time Delta-Time curve Delta_t(s) = t_sim(s) - t_ref(s).
    A positive delta indicates the simulation car is lagging the pole driver;
    a negative delta indicates the simulation car is ahead.
    """
    s_sim = sim_telem.s
    t_sim = sim_telem.time

    s_ref = ref_df["distance_m"].to_numpy()
    t_ref_raw = (pd.to_datetime(ref_df["date"]) - pd.to_datetime(ref_df["date"].iloc[0])).dt.total_seconds().to_numpy()
    
    idx_sort = np.argsort(s_ref)
    s_ref_sorted = s_ref[idx_sort]
    t_ref_sorted = t_ref_raw[idx_sort]

    unique_mask = np.concatenate(([True], np.diff(s_ref_sorted) > 0.1))
    s_ref_clean = s_ref_sorted[unique_mask]
    t_ref_clean = t_ref_sorted[unique_mask]

    t_ref_interp = np.interp(s_sim, s_ref_clean, t_ref_clean)
    delta_t = t_sim - t_ref_interp

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=s_sim, y=delta_t,
            mode='lines', name=f'Delta Time vs {driver_label}',
            line=dict(color="#00e5ff", width=2.0),
            fill='tozeroy',
            fillcolor='rgba(0, 229, 255, 0.15)',
            hovertemplate="Distance: %{x:.1f} m<br>Delta: %{y:+.3f} s<extra></extra>"
        )
    )

    fig.add_hline(y=0.0, line=dict(color="#ffffff", width=1.0, dash="dash"))

    final_delta = delta_t[-1]
    status_text = f"2026 Car is {abs(final_delta):.3f}s {'FASTER' if final_delta < 0 else 'SLOWER'} than {driver_label}"

    fig.update_layout(
        title=dict(
            text=f"Delta Time Trace: {status_text} (Total Sim: {sim_telem.lap_time:.3f}s)",
            font=dict(size=13, color="#00e5ff")
        ),
        xaxis=dict(title="Track Distance (m)", showgrid=True, gridcolor="#1f2937"),
        yaxis=dict(title="Delta Time (s)", showgrid=True, gridcolor="#1f2937", zeroline=True, zerolinecolor="#ffffff"),
        template="plotly_dark",
        height=320,
        margin=dict(l=60, r=40, t=50, b=40),
        paper_bgcolor="#090d16",
        plot_bgcolor="#111827"
    )

    return fig


def export_telemetry_to_mat(sim_telem: LapTelemetry, filepath: str, track: Optional[Track] = None, session_name: str = "F1 2026 LTS") -> str:
    """
    Exports LapTelemetry and optional Track geometry to a native MATLAB .mat workspace file.
    """
    import scipy.io
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    mat_dict = {
        "session_name": session_name,
        "time": sim_telem.time,
        "distance": sim_telem.s,
        "speed_kmh": sim_telem.v_kmh,
        "speed_ms": sim_telem.v,
        "a_x": sim_telem.a_x,
        "a_y": sim_telem.a_y,
        "throttle": sim_telem.throttle,
        "brake": sim_telem.brake,
        "gear": getattr(sim_telem, "gear", np.zeros_like(sim_telem.time)),
        "engine_rpm": getattr(sim_telem, "engine_rpm", np.zeros_like(sim_telem.time)),
        "steering_angle_deg": getattr(sim_telem, "steering_angle_deg", np.zeros_like(sim_telem.time)),
        "p_ice_kw": sim_telem.p_ice_kw,
        "p_mguk_kw": sim_telem.p_mguk_kw,
        "soc_percent": sim_telem.soc_percent,
        "t_tire_c": sim_telem.t_tire_c,
        "f_z_fl": getattr(sim_telem, "f_z_fl", np.zeros_like(sim_telem.time)),
        "f_z_fr": getattr(sim_telem, "f_z_fr", np.zeros_like(sim_telem.time)),
        "f_z_rl": getattr(sim_telem, "f_z_rl", np.zeros_like(sim_telem.time)),
        "f_z_rr": getattr(sim_telem, "f_z_rr", np.zeros_like(sim_telem.time)),
        "f_downforce_n": sim_telem.f_downforce_n,
        "f_drag_n": sim_telem.f_drag_n,
        "lap_time": float(sim_telem.lap_time)
    }
    if track is not None:
        mat_dict["track_name"] = track.name
        mat_dict["track_x"] = track.x
        mat_dict["track_y"] = track.y
        mat_dict["track_z"] = track.z
        mat_dict["track_length"] = float(track.length)

    scipy.io.savemat(filepath, mat_dict)
    return filepath


def _apply_dark_chart_theme(
    fig: go.Figure,
    title: str,
    y_title: str,
    x_title: str = "Track Distance (meters)",
    track: Optional[Track] = None,
    scrub_dist: Optional[float] = None,
    height: int = 340
) -> go.Figure:
    """Applies a clean, high-contrast dark theme with an individual legend on top-right."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14, color="#ffffff", family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif")
        ),
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#090d16",
        height=height,
        margin=dict(l=55, r=25, t=55, b=45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color="#e2e8f0"),
            bgcolor="rgba(11, 15, 25, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.1)",
            borderwidth=1
        ),
        xaxis=dict(
            title=dict(text=x_title, font=dict(size=11, color="#8b949e")),
            gridcolor="#1b2333",
            zerolinecolor="#1b2333",
            tickfont=dict(color="#8b949e", size=10),
            showspikes=True,
            spikethickness=1,
            spikedash="dot",
            spikecolor="#ffa726"
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(size=11, color="#8b949e")),
            gridcolor="#1b2333",
            zerolinecolor="#1b2333",
            tickfont=dict(color="#8b949e", size=10)
        ),
        hovermode="x unified"
    )

    # Sector lines
    if track and hasattr(track, "sectors") and track.sectors:
        for name, s_start, s_end in track.sectors:
            if s_start > 0:
                fig.add_vline(
                    x=s_start,
                    line=dict(color="#374151", width=1.0, dash="dash")
                )

    # Scrub cursor
    if scrub_dist is not None:
        fig.add_vline(
            x=scrub_dist,
            line=dict(color="#ffea00", width=1.8, dash="solid")
        )

    return fig


def create_individual_speed_figure(
    sim_telem: LapTelemetry,
    ref_df: Optional[pd.DataFrame] = None,
    track: Optional[Track] = None,
    driver_label: str = "Real 2025 Pole Lap",
    scrub_dist: Optional[float] = None
) -> go.Figure:
    """Dedicated Speed Comparison chart with its own separate legend."""
    fig = go.Figure()

    # 1. 2026 Simulation Car Speed
    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=sim_telem.v_kmh,
        mode="lines",
        name="🟢 2026 Sim Car",
        line=dict(color="#00ff88", width=2.4),
        hovertemplate="<b>2026 Sim:</b> %{y:.1f} km/h<extra></extra>"
    ))

    # 2. Real Pole Driver Speed
    if ref_df is not None and "distance_m" in ref_df.columns and "speed" in ref_df.columns:
        fig.add_trace(go.Scatter(
            x=ref_df["distance_m"],
            y=ref_df["speed"],
            mode="lines",
            name=f"⚪ {driver_label}",
            line=dict(color="#00e5ff", width=2.0, dash="dot"),
            hovertemplate=f"<b>{driver_label}:</b> %{{y:.1f}} km/h<extra></extra>"
        ))

    # 2026 Regulation Taper Markers
    fig.add_hline(
        y=290.0,
        line=dict(color="#ffa726", width=1.0, dash="dash"),
        annotation_text="2026 MGU-K Taper (290 km/h)",
        annotation_position="top right",
        annotation_font=dict(size=9, color="#ffa726")
    )
    fig.add_hline(
        y=345.0,
        line=dict(color="#ef5350", width=1.0, dash="dash"),
        annotation_text="2026 MGU-K Cutoff (345 km/h)",
        annotation_position="top right",
        annotation_font=dict(size=9, color="#ef5350")
    )

    return _apply_dark_chart_theme(
        fig,
        title="🏎️ Speed Profile Comparison: 2026 Car vs Real Pole Lap",
        y_title="Speed (km/h)",
        track=track,
        scrub_dist=scrub_dist,
        height=320
    )


def create_individual_inputs_figure(
    sim_telem: LapTelemetry,
    ref_df: Optional[pd.DataFrame] = None,
    track: Optional[Track] = None,
    scrub_dist: Optional[float] = None
) -> go.Figure:
    """Dedicated Driver Inputs & Gearing chart with its own separate legend."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=sim_telem.throttle * 100.0,
        mode="lines",
        name="🟢 Gas Pedal (%)",
        line=dict(color="#00ff88", width=1.8),
        hovertemplate="Gas: %{y:.0f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=sim_telem.brake * 100.0,
        mode="lines",
        name="🔴 Brake Pedal (%)",
        line=dict(color="#ff1744", width=1.8),
        fill="tozeroy",
        fillcolor="rgba(255, 23, 68, 0.15)",
        hovertemplate="Brake: %{y:.0f}%<extra></extra>"
    ))

    if hasattr(sim_telem, "gear") and sim_telem.gear is not None:
        fig.add_trace(go.Scatter(
            x=sim_telem.s,
            y=sim_telem.gear * 12.5,  # Scale 1-8 to 0-100%
            mode="lines",
            name="⚪ Gear (1 to 8)",
            line=dict(color="#e2e8f0", width=1.4, shape="hv"),
            hovertemplate="Gear: %{customdata}<extra></extra>",
            customdata=sim_telem.gear
        ))

    return _apply_dark_chart_theme(
        fig,
        title="🎮 Driver Inputs: Gas Pedal, Brake Pedal & Sequential Gearing",
        y_title="Pedal Travel (%)",
        track=track,
        scrub_dist=scrub_dist,
        height=280
    )


def create_individual_powertrain_figure(
    sim_telem: LapTelemetry,
    track: Optional[Track] = None,
    scrub_dist: Optional[float] = None
) -> go.Figure:
    """Dedicated 2026 Hybrid Powertrain Deployment chart with its own separate legend."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=sim_telem.p_ice_kw,
        mode="lines",
        name="🟡 1.6L V6 Petrol Engine (kW)",
        line=dict(color="#ffea00", width=1.8),
        hovertemplate="ICE Engine: %{y:.0f} kW<extra></extra>"
    ))

    # Split MGU-K into Deploy (positive) and Regen (negative)
    mgu_deploy = np.maximum(sim_telem.p_mguk_kw, 0.0)
    mgu_regen = np.minimum(sim_telem.p_mguk_kw, 0.0)

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=mgu_deploy,
        mode="lines",
        name="🟠 350 kW Electric Boost (Deploy)",
        line=dict(color="#ff9100", width=1.8),
        fill="tozeroy",
        fillcolor="rgba(255, 145, 0, 0.18)",
        hovertemplate="Electric Boost: +%{y:.0f} kW<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=mgu_regen,
        mode="lines",
        name="🔵 350 kW Regen Braking (Harvest)",
        line=dict(color="#2979ff", width=1.8),
        fill="tozeroy",
        fillcolor="rgba(41, 121, 255, 0.20)",
        hovertemplate="Harvesting: %{y:.0f} kW<extra></extra>"
    ))

    return _apply_dark_chart_theme(
        fig,
        title="⚡ 2026 Hybrid Powertrain: 400 kW Engine vs 350 kW Electric Motor",
        y_title="Power (kW)",
        track=track,
        scrub_dist=scrub_dist,
        height=280
    )


def create_individual_energy_tires_figure(
    sim_telem: LapTelemetry,
    track: Optional[Track] = None,
    scrub_dist: Optional[float] = None
) -> go.Figure:
    """Dedicated Battery SoC & Tire Temperatures chart with its own separate legend."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=sim_telem.soc_percent,
        mode="lines",
        name="🟣 Battery State-of-Charge (%)",
        line=dict(color="#d500f9", width=2.0),
        hovertemplate="Battery: %{y:.1f}%<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=sim_telem.t_tire_c,
        mode="lines",
        name="🔴 Tire Temperature (°C)",
        line=dict(color="#ff5252", width=1.8, dash="dot"),
        hovertemplate="Tire Temp: %{y:.1f}°C<extra></extra>"
    ))

    return _apply_dark_chart_theme(
        fig,
        title="🔋 Battery Energy Storage (%) & Tire Bulk Temperature (°C)",
        y_title="Level (% / °C)",
        track=track,
        scrub_dist=scrub_dist,
        height=280
    )


def create_individual_chassis_figure(
    sim_telem: LapTelemetry,
    track: Optional[Track] = None,
    scrub_dist: Optional[float] = None
) -> go.Figure:
    """Dedicated 4-Wheel Chassis Load Transfer chart with its own separate legend."""
    fig = go.Figure()

    # Convert vertical loads to kg (N / 9.81) for easy human understanding
    f_front_kg = (getattr(sim_telem, "f_z_fl", np.zeros_like(sim_telem.time)) + 
                  getattr(sim_telem, "f_z_fr", np.zeros_like(sim_telem.time))) / 9.81
    f_rear_kg = (getattr(sim_telem, "f_z_rl", np.zeros_like(sim_telem.time)) + 
                 getattr(sim_telem, "f_z_rr", np.zeros_like(sim_telem.time))) / 9.81
    f_downforce_kg = sim_telem.f_downforce_n / 9.81

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=f_front_kg,
        mode="lines",
        name="🔵 Front Axle Load (kg)",
        line=dict(color="#38bdf8", width=1.8),
        hovertemplate="Front Load: %{y:,.0f} kg<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=f_rear_kg,
        mode="lines",
        name="🔴 Rear Axle Load (kg)",
        line=dict(color="#f43f5e", width=1.8),
        hovertemplate="Rear Load: %{y:,.0f} kg<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=sim_telem.s,
        y=f_downforce_kg,
        mode="lines",
        name="🟢 Aero Downforce (kg)",
        line=dict(color="#00ff88", width=1.6, dash="dash"),
        hovertemplate="Downforce: %{y:,.0f} kg<extra></extra>"
    ))

    return _apply_dark_chart_theme(
        fig,
        title="🛞 Chassis Dynamic Loads & Downforce (kg): Braking & Cornering Transfer",
        y_title="Vertical Load (kg)",
        track=track,
        scrub_dist=scrub_dist,
        height=280
    )


