"""
MoTeC i2 Pro Professional Telemetry Exporter.
Exports 100 Hz simulation telemetry in official MoTeC CSV standard with channel metadata,
engineering units, and a companion MoTeC LDX sector beacon marker XML file.
Can be directly dragged and dropped into MoTeC i2 Pro for professional motorsport analysis.
"""

import os
from typing import Optional
import numpy as np
import pandas as pd

from .track import Track
from .lts_engine import LapTelemetry


def export_to_motec_csv(
    telem: LapTelemetry,
    track: Optional[Any] = None,
    vehicle_name: str = "2026 Formula 1 Concept",
    driver_name: str = "Race Engineer (Sim)",
    filepath: Optional[str] = None,
    session_name: Optional[str] = None,
    **kwargs
) -> str:
    """
    Exports LapTelemetry into official MoTeC i2 Pro CSV format with channel headers and engineering units.
    """
    if isinstance(track, str) and filepath is None:
        filepath = track
        track = None

    venue_name = getattr(track, "name", session_name or "Grand Prix Circuit")
    n_pts = len(telem.time)
    
    # 4-corner tire temperatures (estimate left/right differential based on lateral g)
    t_base = telem.t_tire_c
    ay = telem.a_y
    # Heavily loaded outside tires get hotter than inside tires
    t_fl = t_base + np.clip(-ay * 2.8, -4.0, 12.0)
    t_fr = t_base + np.clip(ay * 2.8, -4.0, 12.0)
    t_rl = t_base + np.clip(-ay * 2.4, -3.0, 10.0)
    t_rr = t_base + np.clip(ay * 2.4, -3.0, 10.0)

    # 4-wheel vertical loads (estimate from downforce and load transfer)
    fz_tot = (888.0 * 9.81) + telem.f_downforce_n
    fz_fl = getattr(telem, "f_z_fl", None)
    if fz_fl is None:
        fz_fl = np.clip(0.22 * fz_tot - telem.a_x * 800.0 - telem.a_y * 1100.0, 300.0, None)
        fz_fr = np.clip(0.22 * fz_tot - telem.a_x * 800.0 + telem.a_y * 1100.0, 300.0, None)
        fz_rl = np.clip(0.28 * fz_tot + telem.a_x * 800.0 - telem.a_y * 950.0, 300.0, None)
        fz_rr = np.clip(0.28 * fz_tot + telem.a_x * 800.0 + telem.a_y * 950.0, 300.0, None)
    else:
        fz_fr = telem.f_z_fr
        fz_rl = telem.f_z_rl
        fz_rr = telem.f_z_rr

    # Gear and RPM
    gear = getattr(telem, "gear", None)
    if gear is None:
        v_kmh = telem.v_kmh
        gear = np.clip(np.floor(v_kmh / 45.0) + 1, 1, 8).astype(int)
        
    engine_rpm = getattr(telem, "engine_rpm", None)
    if engine_rpm is None:
        engine_rpm = np.clip(4500.0 + (telem.v_kmh % 45.0) * 150.0, 4200.0, 12000.0)

    steering_angle_deg = getattr(telem, "steering_angle_deg", None)
    if steering_angle_deg is None and track is not None:
        radius_interp = np.interp(telem.s, track.s, track.corner_radius)
        steering_angle_deg = np.where(radius_interp < 9000.0, (3.4 / radius_interp) * (180.0 / np.pi) * 15.0, 0.0)
    elif steering_angle_deg is None:
        steering_angle_deg = np.zeros_like(telem.time)

    lines = [
        "Format,MoTeC CSV File",
        f"Venue,{venue_name}",
        f"Vehicle,{vehicle_name}",
        f"Driver,{driver_name}",
        "Device,LTS-2026-F1",
        f"Comment,{session_name or '2026 Formula 1 Forward-Euler 0.01s Numerical Lap Time Simulation'}",

        "Log Date,17/10/2026",
        "Log Time,10:30:00",
        "Sample Rate,100",
        "",
        # Channel Names
        "Time,Distance,Corr Speed,Throttle Pos,Brake Press,Gear,Engine RPM,G Force Lat,G Force Long,Steering Angle,MGU-K Power,Battery SoC,Tire Temp FL,Tire Temp FR,Tire Temp RL,Tire Temp RR,Wheel Load FL,Wheel Load FR,Wheel Load RL,Wheel Load RR,Downforce Total,Aero Drag,Tire Mu Eff",
        # Channel Units
        "s,m,km/h,%,%,,rpm,g,g,deg,kW,%,C,C,C,C,N,N,N,N,N,N,"
    ]

    for i in range(n_pts):
        row = [
            f"{telem.time[i]:.3f}",
            f"{telem.s[i]:.2f}",
            f"{telem.v_kmh[i]:.2f}",
            f"{telem.throttle[i] * 100.0:.1f}",
            f"{telem.brake[i] * 100.0:.1f}",
            f"{gear[i]}",
            f"{engine_rpm[i]:.0f}",
            f"{telem.a_y[i]:.3f}",
            f"{telem.a_x[i]:.3f}",
            f"{steering_angle_deg[i]:.1f}",
            f"{telem.p_mguk_kw[i]:.1f}",
            f"{telem.soc_percent[i]:.2f}",
            f"{t_fl[i]:.1f}",
            f"{t_fr[i]:.1f}",
            f"{t_rl[i]:.1f}",
            f"{t_rr[i]:.1f}",
            f"{fz_fl[i]:.0f}",
            f"{fz_fr[i]:.0f}",
            f"{fz_rl[i]:.0f}",
            f"{fz_rr[i]:.0f}",
            f"{telem.f_downforce_n[i]:.0f}",
            f"{telem.f_drag_n[i]:.0f}",
            f"{telem.mu_eff[i]:.3f}"
        ]
        lines.append(",".join(row))

    csv_content = "\n".join(lines)
    
    if filepath:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(csv_content)
            
    return csv_content


def export_to_motec_ldx_beacon(
    track: Track,
    telem: Optional[LapTelemetry] = None,
    filepath: Optional[str] = None
) -> str:
    """
    Generates a companion MoTeC LDX XML file containing start/finish line and sector beacons.
    """
    total_time = telem.lap_time if telem is not None else 80.0
    
    beacons_xml = [
        '<?xml version="1.0"?>',
        '<LDXFile Version="1.6" Locale="English_United States.1252">',
        '  <Layers>',
        '    <Layer>',
        '      <MarkerBlock>',
        '        <MarkerVersion>1</MarkerVersion>',
        '        <Markers>'
    ]
    
    # Start Beacon
    beacons_xml.append(f'          <Marker Flags="0" Time="0.000000" Name="Out Lap / Start" />')
    
    # Timing Sector Beacons
    for sec_name, s_start, s_end in track.sectors:
        if telem is not None and len(telem.s) > 0:
            idx = int(np.clip(np.searchsorted(telem.s, s_end), 0, len(telem.time) - 1))
            t_sec = telem.time[idx]
        else:
            fraction = s_end / track.length if track.length > 0 else 0.33
            t_sec = total_time * fraction
        beacons_xml.append(f'          <Marker Flags="0" Time="{t_sec * 1e6:.0f}" Name="{sec_name}" />')
        
    beacons_xml.append(f'          <Marker Flags="0" Time="{total_time * 1e6:.0f}" Name="Finish Line" />')
    beacons_xml.extend([
        '        </Markers>',
        '      </MarkerBlock>',
        '    </Layer>',
        '  </Layers>',
        '</LDXFile>'
    ])
    
    ldx_content = "\n".join(beacons_xml)
    if filepath:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ldx_content)
            
    return ldx_content


# Functional Aliases
export_motec_csv = export_to_motec_csv
export_motec_ldx = export_to_motec_ldx_beacon


class MoTecExporter:
    """Convenience class providing MoTeC i2 Pro telemetry and beacon export utilities."""
    @staticmethod
    def export_csv(telem: LapTelemetry, track: Track, filepath: Optional[str] = None, vehicle_name: str = "2026 Formula 1 Concept", driver_name: str = "Sim Engineer") -> str:
        return export_to_motec_csv(telem, track, vehicle_name, driver_name, filepath)

    @staticmethod
    def export_ldx(track: Track, telem: Optional[LapTelemetry] = None, filepath: Optional[str] = None) -> str:
        return export_to_motec_ldx_beacon(track, telem, filepath)

