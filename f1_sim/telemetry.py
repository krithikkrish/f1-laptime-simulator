"""
Motorsport Telemetry Visualization & Analysis Suite.
Generates publication-quality telemetry figures:
1. Multi-channel race engineer dashboard (Speed, Throttle/Brake, Gear, SoC, MGU-K Power, Tire Temp)
2. GG Acceleration Diagram (Friction circle validation)
3. 2D Circuit Speed & Energy Heatmaps
4. Comparative Overlay: Baseline vs Optimized Hybrid Strategy
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap

from .track import Track
from .lts_engine import LapTelemetry


# Dark sleek motorsport theme
plt.style.use('dark_background')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#444444'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#2a2a2a'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.7


def plot_telemetry_dashboard(telem: LapTelemetry, track: Track, save_path: str = None) -> plt.Figure:
    """
    Renders the multi-channel Race Engineer Telemetry Dashboard.
    Channels:
    - Speed (km/h) with 290 km/h FIA MGU-K taper line
    - Driver Inputs (Throttle & Brake %)
    - 2026 MGU-K Hybrid Power (kW: positive deploy, negative harvest)
    - Battery State of Charge (SoC %)
    - Tire Bulk Temperature (°C) & Thermal Friction Efficiency (mu)
    """
    fig, axes = plt.subplots(5, 1, figsize=(14, 12), sharex=True, gridspec_kw={'height_ratios': [2.2, 1.2, 1.5, 1.3, 1.3]})
    fig.suptitle(f"2026 F1 Lap-Time Simulation Telemetry — {track.name}\nLap Time: {telem.lap_time:.3f} s | Top Speed: {np.max(telem.v_kmh):.1f} km/h | Net Deploy: {telem.net_energy_deployed_mj:.2f} MJ", 
                 fontsize=14, fontweight='bold', color='#00e5ff', y=0.98)

    s = telem.s

    # 1. Speed Profile
    ax_spd = axes[0]
    ax_spd.plot(s, telem.v_kmh, color='#00ff88', linewidth=1.6, label='Velocity (km/h)')
    ax_spd.axhline(290.0, color='#ff9100', linestyle=':', alpha=0.8, label='2026 MGU-K Taper Threshold (290 km/h)')
    ax_spd.axhline(345.0, color='#ff1744', linestyle=':', alpha=0.8, label='2026 MGU-K Cutoff (345 km/h)')
    ax_spd.set_ylabel("Speed\n(km/h)", fontsize=10, fontweight='bold', color='#00ff88')
    ax_spd.set_ylim(40, 360)
    ax_spd.grid(True)
    ax_spd.legend(loc='lower left', framealpha=0.4, fontsize=8)

    # Annotate sector boundaries
    for sec_name, s_start, s_end in track.sectors:
        ax_spd.axvline(s_end, color='#555555', linestyle='--', alpha=0.6)
        ax_spd.text(s_end - 120, 55, sec_name, color='#888888', fontsize=8, rotation=90)

    # 2. Driver Pedals (Throttle & Brake)
    ax_ped = axes[1]
    ax_ped.plot(s, telem.throttle * 100.0, color='#00e5ff', linewidth=1.4, label='Throttle (%)')
    ax_ped.plot(s, telem.brake * 100.0, color='#ff1744', linewidth=1.4, label='Brake (%)')
    ax_ped.set_ylabel("Pedals\n(%)", fontsize=10, fontweight='bold', color='#ffffff')
    ax_ped.set_ylim(-5, 105)
    ax_ped.grid(True)
    ax_ped.legend(loc='upper right', framealpha=0.4, fontsize=8)

    # 3. 2026 MGU-K Hybrid Power (Deploy vs Harvest)
    ax_pwr = axes[2]
    # Fill deploy in cyan, harvest in lime
    p_mguk = telem.p_mguk_kw
    ax_pwr.fill_between(s, np.maximum(0, p_mguk), 0, color='#00e5ff', alpha=0.4, label='MGU-K Deploy (+350 kW max)')
    ax_pwr.fill_between(s, np.minimum(0, p_mguk), 0, color='#76ff03', alpha=0.4, label='MGU-K Regen Harvest (-350 kW max)')
    ax_pwr.plot(s, p_mguk, color='#ffffff', linewidth=0.8)
    ax_pwr.axhline(0, color='#666666', linestyle='-', linewidth=0.8)
    ax_pwr.axhline(350.0, color='#00e5ff', linestyle='--', alpha=0.5)
    ax_pwr.axhline(-350.0, color='#76ff03', linestyle='--', alpha=0.5)
    ax_pwr.set_ylabel("MGU-K Power\n(kW)", fontsize=10, fontweight='bold', color='#00e5ff')
    ax_pwr.set_ylim(-380, 380)
    ax_pwr.grid(True)
    ax_pwr.legend(loc='upper right', framealpha=0.4, fontsize=8)

    # 4. Battery State of Charge (SoC %)
    ax_soc = axes[3]
    ax_soc.plot(s, telem.soc_percent, color='#ffd600', linewidth=1.6, label='Battery SoC (%)')
    ax_soc.axhline(5.0, color='#ff1744', linestyle='--', alpha=0.8, label='Emergency Safety Floor (5%)')
    ax_soc.set_ylabel("Battery SoC\n(%)", fontsize=10, fontweight='bold', color='#ffd600')
    ax_soc.set_ylim(0, 100)
    ax_soc.grid(True)
    ax_soc.legend(loc='lower left', framealpha=0.4, fontsize=8)

    # 5. Tire Bulk Temperature & Friction Coefficient
    ax_tir = axes[4]
    ax_tir.plot(s, telem.t_tire_c, color='#ff6d00', linewidth=1.6, label='Tire Temp (°C)')
    ax_tir.axhline(100.0, color='#00ff88', linestyle=':', alpha=0.7, label='Optimal Thermal Window (100°C)')
    ax_tir.set_ylabel("Tire Temp\n(°C)", fontsize=10, fontweight='bold', color='#ff6d00')
    ax_tir.set_xlabel("Track Distance s (meters)", fontsize=11, fontweight='bold', color='#ffffff')
    ax_tir.set_ylim(70, 135)
    ax_tir.grid(True)

    # Secondary axis for grip coefficient mu
    ax_mu = ax_tir.twinx()
    ax_mu.plot(s, telem.mu_eff, color='#e040fb', linestyle='--', linewidth=1.2, label='Friction Coeff μ')
    ax_mu.set_ylabel("Tire μ", fontsize=10, fontweight='bold', color='#e040fb')
    ax_mu.set_ylim(1.0, 2.0)

    # Combine legends
    lines_1, labels_1 = ax_tir.get_legend_handles_labels()
    lines_2, labels_2 = ax_mu.get_legend_handles_labels()
    ax_tir.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right', framealpha=0.4, fontsize=8)

    plt.tight_layout(rect=[0, 0.02, 1, 0.95])

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=200, bbox_inches='tight')
        print(f"[*] Telemetry Dashboard saved to: {save_path}")

    return fig


def plot_gg_diagram(telem: LapTelemetry, save_path: str = None) -> plt.Figure:
    """
    Renders the GG Diagram (lateral acceleration a_y vs longitudinal acceleration a_x in g).
    Validates adherence to the combined tire friction ellipse (Pacejka limits).
    """
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_title("Vehicle GG Acceleration Diagram (g-g Friction Envelope)", fontsize=12, fontweight='bold', color='#00e5ff', pad=15)

    scatter = ax.scatter(telem.a_y, telem.a_x, c=telem.v_kmh, cmap='plasma', s=4, alpha=0.6, edgecolors='none')
    cbar = fig.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Speed (km/h)", fontsize=9, color='#ffffff')

    # Draw friction ellipse boundary approximations for low, medium, and high downforce speeds
    angles = np.linspace(0, 2 * np.pi, 200)
    for g_lat, g_long, label, col in [(2.0, 1.8, 'Low Speed (100 km/h)', '#555555'),
                                      (3.5, 3.2, 'Medium Speed (220 km/h)', '#777777'),
                                      (5.0, 4.5, 'High Speed Downforce (300 km/h)', '#00e5ff')]:
        ax.plot(g_lat * np.cos(angles), g_long * np.sin(angles), linestyle='--', color=col, linewidth=1.0, alpha=0.6, label=label)

    ax.set_xlabel("Lateral Acceleration ay (g)", fontsize=10, fontweight='bold')
    ax.set_ylabel("Longitudinal Acceleration ax (g: +accel / -brake)", fontsize=10, fontweight='bold')
    ax.set_xlim(-6.0, 6.0)
    ax.set_ylim(-6.0, 4.0)
    ax.axhline(0, color='#444444', linewidth=0.8)
    ax.axvline(0, color='#444444', linewidth=0.8)
    ax.grid(True)
    ax.legend(loc='lower left', fontsize=8, framealpha=0.4)
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=200, bbox_inches='tight')
        print(f"[*] GG Diagram saved to: {save_path}")

    return fig


def plot_track_map(track: Track, telem: LapTelemetry = None, save_path: str = None) -> plt.Figure:
    """
    Renders official 2D GPS circuit map with speed color-gradient, corner callouts,
    and start/finish line.
    """
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_title(f"Circuit Layout & Speed Telemetry Map — {track.name}", 
                 fontsize=13, fontweight='bold', color='#00e5ff', pad=15)

    # 1. Plot track speed profile line collection
    if telem is not None:
        v_interp = np.interp(track.s, telem.s, telem.v_kmh)
        points = np.array([track.x, track.y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        norm = plt.Normalize(v_interp.min(), v_interp.max())
        lc = LineCollection(segments, cmap='turbo', norm=norm, linewidth=4.5, zorder=3)
        lc.set_array(v_interp)
        line = ax.add_collection(lc)

        # Ambient glow behind track line
        lc_glow = LineCollection(segments, cmap='turbo', norm=norm, linewidth=8.0, alpha=0.25, zorder=2)
        lc_glow.set_array(v_interp)
        ax.add_collection(lc_glow)

        cbar = fig.colorbar(line, ax=ax, fraction=0.035, pad=0.04)
        cbar.set_label("Speed (km/h)", fontsize=10, color='#ffffff')
    else:
        ax.plot(track.x, track.y, color='#00e5ff', linewidth=4.0, zorder=3)

    # 2. Key Corner Landmarks & Annotations with exact FIA track apex locations
    landmarks = []
    if "Monza" in track.name:
        landmarks = [
            ("Start / Finish", 0.0, (25, 10)),
            ("Variante del Rettifilo\n(T1-T2 Chicane)", 635.0, (20, 10)),
            ("Curva Biassono\n(Curva Grande - T3)", 1310.0, (-100, 20)),
            ("Variante della Roggia\n(T4-T5 Chicane)", 1860.0, (-110, 15)),
            ("Curva di Lesmo 1 (T6)", 2195.0, (15, 18)),
            ("Curva di Lesmo 2 (T7)", 2285.0, (15, 5)),
            ("Curva del Serraglio", 2575.0, (20, 10)),
            ("Variante Ascari\n(T8-T9-T10 Chicane)", 3720.0, (20, 12)),
            ("Curva Parabolica\n(Alboreto - T11)", 4950.0, (20, -15)),
        ]
    elif "Silverstone" in track.name:
        landmarks = [
            ("Start / Finish\n(Hamilton Straight)", 0.0, (20, -30)),
            ("Abbey (T1)", 120.0, (18, 12)),
            ("Farm Curve (T2)", 330.0, (18, 10)),
            ("Village (T3)", 600.0, (18, 10)),
            ("The Loop (T4)", 740.0, (-85, -15)),
            ("Aintree (T5)", 950.0, (18, 5)),
            ("Wellington Straight", 1300.0, (18, 10)),
            ("Brooklands (T6)", 1660.0, (15, 15)),
            ("Luffield (T7)", 1880.0, (-80, 10)),
            ("Woodcote (T8)", 2280.0, (-40, 18)),
            ("National Straight", 2500.0, (-30, 18)),
            ("Copse (T9)", 2780.0, (20, 12)),
            ("Maggotts (T10-T11)", 3410.0, (20, 10)),
            ("Becketts (T12-T13)", 3600.0, (20, 8)),
            ("Chapel (T14)", 3740.0, (18, -12)),
            ("Hangar Straight", 4250.0, (18, 10)),
            ("Stowe (T15)", 4740.0, (18, -10)),
            ("Vale (T16 Chicane)", 5220.0, (18, 10)),
            ("Club (T17-T18)", 5400.0, (-85, 10)),
        ]

    for item in landmarks:
        label = item[0]
        s_val = item[1]
        offset = item[2] if len(item) > 2 else (12, 12)
        idx = int(np.clip(np.searchsorted(track.s, s_val), 0, len(track.x) - 1))
        x_pt, y_pt = track.x[idx], track.y[idx]

        if "Start" in label:
            # Mark Start/Finish with red diamond
            ax.scatter(x_pt, y_pt, color='#ff1744', s=150, marker='D', edgecolor='#ffffff', linewidth=1.8, zorder=6, label='Start / Finish')
            ax.annotate(label, (x_pt, y_pt), xytext=offset, textcoords='offset points',
                        fontsize=9.5, fontweight='bold', color='#ffffff',
                        bbox=dict(boxstyle="round,pad=0.35", fc="#ff1744", ec="none", alpha=0.9),
                        arrowprops=dict(arrowstyle="->", color="#ffffff", lw=1.3), zorder=7)
        else:
            # Mark corners with cyan dots and clean callout boxes
            ax.scatter(x_pt, y_pt, color='#00e5ff', s=45, edgecolor='#ffffff', linewidth=0.8, zorder=5)
            ax.annotate(label, (x_pt, y_pt), xytext=offset, textcoords='offset points',
                        fontsize=7.5, color='#e0e0e0',
                        bbox=dict(boxstyle="round,pad=0.25", fc="#161b22", ec="#30363d", alpha=0.85),
                        arrowprops=dict(arrowstyle="->", color="#8b949e", lw=0.8), zorder=6)

    # 3. Framing & Aspect
    ax.set_aspect('equal', 'datalim')
    margin_x = (track.x.max() - track.x.min()) * 0.12
    margin_y = (track.y.max() - track.y.min()) * 0.12
    ax.set_xlim(track.x.min() - margin_x, track.x.max() + margin_x)
    ax.set_ylim(track.y.min() - margin_y, track.y.max() + margin_y)
    ax.axis('off')
    ax.legend(loc='lower right', framealpha=0.5, fontsize=9)
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=200, bbox_inches='tight')
        print(f"[*] Track Map saved to: {save_path}")

    return fig


def plot_strategy_comparison(base: LapTelemetry, opt: LapTelemetry, track: Track, save_path: str = None) -> plt.Figure:
    """
    Overlays Baseline vs Optimized Hybrid Strategy telemetry.
    Highlights time gain delta and battery energy conservation.
    """
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [2.0, 1.2, 1.2, 1.0]})
    delta_t = base.lap_time - opt.lap_time
    fig.suptitle(f"2026 Hybrid Strategy Optimization Comparison — {track.name}\n"
                 f"Baseline: {base.lap_time:.3f} s (End SoC: {base.soc_percent[-1]:.1f}%) | "
                 f"Optimized: {opt.lap_time:.3f} s (End SoC: {opt.soc_percent[-1]:.1f}%) | "
                 f"Lap Time Gain: {delta_t:+.3f} s",
                 fontsize=13, fontweight='bold', color='#00e5ff', y=0.98)

    s = opt.s

    # Interpolate baseline onto opt distance grid for delta calculations
    v_base_interp = np.interp(s, base.s, base.v_kmh)
    p_base_interp = np.interp(s, base.s, base.p_mguk_kw)
    soc_base_interp = np.interp(s, base.s, base.soc_percent)
    t_base_interp = np.interp(s, base.s, base.time)
    t_opt_interp = opt.time
    delta_time = t_base_interp - t_opt_interp

    # 1. Speed Comparison
    axes[0].plot(s, v_base_interp, color='#888888', linestyle='--', linewidth=1.3, label=f'Baseline (Lap: {base.lap_time:.2f}s)')
    axes[0].plot(s, opt.v_kmh, color='#00ff88', linewidth=1.6, label=f'Optimized (Lap: {opt.lap_time:.2f}s)')
    axes[0].set_ylabel("Speed\n(km/h)", fontsize=10, fontweight='bold', color='#00ff88')
    axes[0].set_ylim(40, 360)
    axes[0].grid(True)
    axes[0].legend(loc='lower left', framealpha=0.4, fontsize=8)

    # 2. Cumulative Delta Time
    axes[1].plot(s, delta_time, color='#00e5ff', linewidth=1.5, label='Time Delta (Baseline - Optimized) [s]')
    axes[1].axhline(0, color='#666666', linestyle=':')
    axes[1].set_ylabel("Delta Time\n(s)", fontsize=10, fontweight='bold', color='#00e5ff')
    axes[1].grid(True)
    axes[1].legend(loc='upper left', framealpha=0.4, fontsize=8)

    # 3. MGU-K Power Allocation Comparison
    axes[2].plot(s, p_base_interp, color='#888888', linestyle=':', linewidth=1.2, label='Baseline MGU-K (kW)')
    axes[2].plot(s, opt.p_mguk_kw, color='#e040fb', linewidth=1.4, label='Optimized Tactical MGU-K (kW)')
    axes[2].set_ylabel("MGU-K Power\n(kW)", fontsize=10, fontweight='bold', color='#e040fb')
    axes[2].set_ylim(-380, 380)
    axes[2].grid(True)
    axes[2].legend(loc='upper right', framealpha=0.4, fontsize=8)

    # 4. Battery SoC Comparison
    axes[3].plot(s, soc_base_interp, color='#888888', linestyle='--', linewidth=1.3, label=f'Baseline SoC (Final: {base.soc_percent[-1]:.1f}%)')
    axes[3].plot(s, opt.soc_percent, color='#ffd600', linewidth=1.6, label=f'Optimized SoC (Final: {opt.soc_percent[-1]:.1f}%)')
    axes[3].axhline(5.0, color='#ff1744', linestyle=':', alpha=0.7, label='5% Floor')
    axes[3].set_ylabel("Battery SoC\n(%)", fontsize=10, fontweight='bold', color='#ffd600')
    axes[3].set_xlabel("Track Distance s (meters)", fontsize=11, fontweight='bold', color='#ffffff')
    axes[3].set_ylim(0, 100)
    axes[3].grid(True)
    axes[3].legend(loc='lower left', framealpha=0.4, fontsize=8)

    plt.tight_layout(rect=[0, 0.02, 1, 0.95])

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=200, bbox_inches='tight')
        print(f"[*] Comparison Plot saved to: {save_path}")

    return fig
