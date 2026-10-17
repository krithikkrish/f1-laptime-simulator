#!/usr/bin/env python3
"""
Run Transient Lap-Time Simulation (0.01s Forward-Euler Integrator).
Simulates a 2026 F1 car around Autodromo Nazionale Monza or Silverstone GP.
Generates comprehensive motorsport telemetry reports and telemetry figures.
"""

import os
import argparse
import numpy as np

from f1_sim import (
    VehicleParams,
    create_monza_track,
    create_silverstone_track,
    SimulationEngine,
    plot_telemetry_dashboard,
    plot_gg_diagram,
    plot_track_map
)


def format_lap_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}:{secs:06.3f}"


def main():
    parser = argparse.ArgumentParser(description="2026 F1 Transient Lap-Time Simulator")
    parser.add_argument("--track", default="monza", help="Circuit to simulate (e.g. monza, silverstone, spa, monaco, suzuka, bahrain, austin, etc.)")
    parser.add_argument("--setup", choices=["balanced", "monza", "monaco", "wet"], default="monza", help="Engineering setup preset")
    parser.add_argument("--dt", type=float, default=0.01, help="Forward-Euler time step (seconds)")
    parser.add_argument("--output_dir", default="output", help="Directory to save telemetry and exports")
    parser.add_argument("--soc_initial", type=float, default=0.70, help="Initial Battery SoC (0.0 - 1.0)")
    parser.add_argument("--export_motec", action="store_true", help="Export official MoTeC i2 Pro CSV and LDX beacon files")
    parser.add_argument("--export_matlab", action="store_true", help="Export session to native MATLAB .mat workspace")
    args = parser.parse_args()

    # 1. Setup Parameters and Track
    preset_map = {
        "balanced": "Balanced Grand Prix Spec",
        "monza": "Monza Low-Drag Spec",
        "monaco": "High-Downforce Monaco Spec",
        "wet": "Wet-Weather Spec"
    }
    setup_name = preset_map.get(args.setup, "Balanced Grand Prix Spec")
    from f1_sim import HOMOLOGATED_PRESETS, export_motec_csv, export_motec_ldx
    from f1_sim.interactive_plots import export_telemetry_to_mat
    from f1_sim.tracks_data import create_calendar_track
    
    setup = HOMOLOGATED_PRESETS.get(setup_name, HOMOLOGATED_PRESETS["Balanced Grand Prix Spec"])
    params = setup.to_vehicle_params()
    params.dt = args.dt
    params.soc_initial = args.soc_initial

    track, weather, meta = create_calendar_track(args.track, ds=1.0)


    print("=" * 75)
    print("      2026 F1 TRANSIENT LAP-TIME & DUAL-TRACK SIMULATOR (LTS)      ")
    print("=" * 75)
    print(f" Circuit:           {track.name}")
    print(f" Track Length:      {track.length:,.1f} meters")
    print(f" Engineering Setup: {setup.name} ({setup.description})")
    print(f" Integration dt:    {params.dt} seconds ({int(1/params.dt)} Hz Forward-Euler)")
    print(f" Total Mass:        {params.total_mass:.1f} kg (Car {params.mass_empty}kg + Fuel {params.fuel_mass}kg + Driver {params.mass_driver}kg)")
    print(f" 4-Wheel Chassis:   Wheelbase {params.wheelbase}m | Track {params.track_width}m | CoG h={0.315}m")
    print(f" Suspension ARB:    Front ARB {setup.front_arb_stiffness_n_mm} N/mm | Rear ARB {setup.rear_arb_stiffness_n_mm} N/mm")
    print(f" Powertrain:        400 kW ICE + 350 kW MGU-K (FIA Taper above 290 km/h)")
    print(f" Transmission:      8-Speed Sequential Seamless-Shift (15ms cuts)")
    print(f" Aerodynamics:      Active Aero (Z-Mode ClA={setup.cl_a_z_mode:.2f} / X-Mode CdA={setup.cd_a_x_mode:.2f})")
    print(f" Brake System:      BBW Migration (Static {setup.brake_bias_front_pct:.1f}% -> Dynamic Migration)")
    print(f" Initial Battery:   {args.soc_initial * 100.0:.1f}% SoC ({args.soc_initial * params.battery_capacity_joules / 1e6:.2f} MJ)")
    print("-" * 75)

    # 2. Run Forward-Euler Numerical Simulation
    engine = SimulationEngine(params)
    print(f"[*] Executing 0.01s Forward-Euler ODE Integration Loop (4-Wheel & Transmission)...")
    telem = engine.run_transient_simulation(track, initial_soc=args.soc_initial)

    # 3. Compute Sector Times
    sector_times = []
    for sec_name, s_start, s_end in track.sectors:
        idx_start = np.searchsorted(telem.s, s_start)
        idx_end = min(len(telem.s) - 1, np.searchsorted(telem.s, s_end))
        t_sec = telem.time[idx_end] - telem.time[idx_start]
        sector_times.append((sec_name, t_sec))

    # 4. Telemetry Statistics Summary
    avg_speed_kmh = (telem.distance_total / telem.lap_time) * 3.6
    top_speed_kmh = np.max(telem.v_kmh)
    min_speed_kmh = np.min(telem.v_kmh)
    peak_brake_g = np.min(telem.a_x)
    peak_accel_g = np.max(telem.a_x)
    peak_lat_g = np.max(telem.a_y)
    peak_tire_temp = np.max(telem.t_tire_c)
    final_soc = telem.soc_percent[-1]
    min_soc = np.min(telem.soc_percent)
    x_mode_ratio = np.mean(telem.aero_mode == "X_MODE") * 100.0

    # 4-Wheel and Transmission statistics
    max_fz_outer = max(np.max(telem.f_z_fl), np.max(telem.f_z_fr), np.max(telem.f_z_rl), np.max(telem.f_z_rr))
    min_fz_inner = min(np.min(telem.f_z_fl), np.min(telem.f_z_fr), np.min(telem.f_z_rl), np.min(telem.f_z_rr))
    gear_shifts = int(np.sum(np.diff(telem.gear) != 0)) if len(telem.gear) > 1 else 0
    max_engine_rpm = np.max(telem.engine_rpm) if len(telem.engine_rpm) > 0 else 0.0
    max_steer_deg = np.max(np.abs(telem.steering_angle_deg)) if len(telem.steering_angle_deg) > 0 else 0.0

    print("\n" + "=" * 75)
    print("                    MOTORSPORT ENGINEERING RESULTS                   ")
    print("=" * 75)
    print(f"  LAP TIME:              {format_lap_time(telem.lap_time)}  ({telem.lap_time:.3f} s)")
    for sec_name, t_sec in sector_times:
        print(f"    ├─ {sec_name:10s}        {t_sec:.3f} s")
    print(f"  Top Speed:             {top_speed_kmh:.1f} km/h")
    print(f"  Average Speed:         {avg_speed_kmh:.1f} km/h")
    print(f"  Min Apex Speed:        {min_speed_kmh:.1f} km/h")
    print("-" * 75)
    print(f"  Peak Braking G:        {peak_brake_g:.2f} g")
    print(f"  Peak Acceleration G:   +{peak_accel_g:.2f} g")
    print(f"  Peak Lateral Grip G:   {peak_lat_g:.2f} g")
    print(f"  Peak Tire Bulk Temp:   {peak_tire_temp:.1f} °C (Optimum: {params.t_tire_opt}°C)")
    print("-" * 75)
    print(f"  4-Wheel Normal Load:   Max Outer: {max_fz_outer:.0f} N | Min Inner: {min_fz_inner:.0f} N")
    print(f"  Max Steering Angle:    {max_steer_deg:.1f}°")
    bbw_text = f"{np.min(telem.bbw_front_pct):.1f}% -> {np.max(telem.bbw_front_pct):.1f}% Front" if telem.bbw_front_pct is not None else "56.5% Front"
    print(f"  BBW Brake Migration:   {bbw_text}")

    print("-" * 75)
    print(f"  MGU-K Energy Deployed: {telem.net_energy_deployed_mj:.2f} MJ (FIA Cap: 4.00 MJ)")
    print(f"  MGU-K Energy Harvest:  {telem.net_energy_harvested_mj:.2f} MJ")
    print(f"  Battery SoC Start/End: {telem.soc_percent[0]:.1f}% ➔ {final_soc:.1f}% (Δ = {telem.delta_soc_percent:+.1f}%)")
    print(f"  Minimum Battery SoC:   {min_soc:.1f}% (Floor: 5.0%)")
    print(f"  Active Aero Straight:  {x_mode_ratio:.1f}% in X-Mode (Low Drag)")
    print("=" * 75)

    # 5. Render & Save Visualizations
    os.makedirs(args.output_dir, exist_ok=True)
    track_prefix = args.track.lower()

    dash_path = os.path.join(args.output_dir, f"{track_prefix}_telemetry_dashboard.png")
    gg_path = os.path.join(args.output_dir, f"{track_prefix}_gg_diagram.png")
    map_path = os.path.join(args.output_dir, f"{track_prefix}_track_map.png")

    plot_telemetry_dashboard(telem, track, save_path=dash_path)
    plot_gg_diagram(telem, save_path=gg_path)
    plot_track_map(track, telem, save_path=map_path)
    print(f"\n[✓] Telemetry dashboards successfully rendered in '{args.output_dir}/'.")

    # 6. Optional Exports (MoTeC i2 Pro & MATLAB)
    if args.export_motec:
        motec_csv_path = os.path.join(args.output_dir, f"{track_prefix}_motec.csv")
        motec_ldx_path = os.path.join(args.output_dir, f"{track_prefix}_motec.ldx")
        export_motec_csv(telem, track=track, filepath=motec_csv_path, session_name=f"{track.name} 2026 LTS")
        export_motec_ldx(track=track, telem=telem, filepath=motec_ldx_path)
        print(f"[✓] MoTeC i2 Pro CSV exported: {motec_csv_path}")
        print(f"[✓] MoTeC i2 Pro LDX beacons exported: {motec_ldx_path}")

    if args.export_matlab:
        mat_path = os.path.join(args.output_dir, f"{track_prefix}_session.mat")
        export_telemetry_to_mat(telem, filepath=mat_path, track=track, session_name=f"{track.name} 2026")
        print(f"[✓] Native MATLAB R2026a workspace exported: {mat_path}\n")




if __name__ == "__main__":
    main()
