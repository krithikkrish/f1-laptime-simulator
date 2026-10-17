#!/usr/bin/env python3
"""
Run Hybrid Energy Deployment Optimization Loop.
Finds the optimal MGU-K 350kW deployment strategy around a track using
Genetic Algorithm (Differential Evolution) or Scipy optimization to minimize
lap time while respecting battery SoC and tire thermal constraints.
"""

import os
import argparse
import numpy as np

from f1_sim import (
    VehicleParams,
    create_monza_track,
    create_silverstone_track,
    SimulationEngine,
    DeploymentOptimizer,
    plot_strategy_comparison
)


def format_lap_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}:{secs:06.3f}"


def main():
    parser = argparse.ArgumentParser(description="2026 F1 Hybrid Deployment Optimization Loop")
    parser.add_argument("--track", choices=["monza", "silverstone"], default="monza", help="Circuit to optimize")
    parser.add_argument("--method", choices=["differential_evolution", "powell"], default="differential_evolution", help="Optimization algorithm")
    parser.add_argument("--zones", type=int, default=12, help="Number of tactical track deployment control zones")
    parser.add_argument("--max_iter", type=int, default=20, help="Maximum optimizer iterations")
    parser.add_argument("--output_dir", default="output", help="Directory to save telemetry comparison")
    args = parser.parse_args()

    # Setup
    params = VehicleParams()
    if args.track == "monza":
        track = create_monza_track(ds=1.0)
    else:
        track = create_silverstone_track(ds=1.0)

    print("=" * 70)
    print("      2026 F1 HYBRID DEPLOYMENT OPTIMIZATION ENGINE      ")
    print("=" * 70)
    print(f" Circuit:           {track.name} ({track.length:,.1f} m)")
    print(f" Optimization Goal: Minimize Lap Time T_lap")
    print(f" Strategy Control:  {args.zones} Dynamic Tactical Deployment Zones")
    print(f" Constraints:       Battery SoC >= 5% | 2026 FIA MGU-K Tapering (>290 km/h)")
    print(f" Optimizer Method:  {args.method.upper()}")
    print("-" * 70)

    engine = SimulationEngine(params)
    optimizer = DeploymentOptimizer(engine, num_zones=args.zones)

    # Run Optimization Loop
    result = optimizer.optimize_hybrid_deployment(
        track=track,
        method=args.method,
        max_iter=args.max_iter
    )

    base = result.baseline_telemetry
    opt = result.optimized_telemetry

    print("\n" + "=" * 70)
    print("                OPTIMIZATION RESULTS SUMMARY             ")
    print("=" * 70)
    print(f"  Baseline Lap Time:     {format_lap_time(base.lap_time)}  ({base.lap_time:.3f} s)")
    print(f"  Optimized Lap Time:    {format_lap_time(opt.lap_time)}  ({opt.lap_time:.3f} s)")
    print(f"  LAP TIME DELTA:        {result.time_delta_seconds:+.3f} seconds faster")
    print("-" * 70)
    print(f"  Baseline Energy Deploy: {base.net_energy_deployed_mj:.2f} MJ (Harvest: {base.net_energy_harvested_mj:.2f} MJ)")
    print(f"  Optimized Energy Deploy:{opt.net_energy_deployed_mj:.2f} MJ (Harvest: {opt.net_energy_harvested_mj:.2f} MJ)")
    print(f"  Baseline End SoC:       {base.soc_percent[-1]:.1f}% (Δ = {base.delta_soc_percent:+.1f}%)")
    print(f"  Optimized End SoC:      {opt.soc_percent[-1]:.1f}% (Δ = {opt.delta_soc_percent:+.1f}%)")
    print(f"  Peak Tire Temperature:  {np.max(opt.t_tire_c):.1f} °C (Baseline: {np.max(base.t_tire_c):.1f} °C)")
    print("=" * 70)

    # Save Comparison Plot
    os.makedirs(args.output_dir, exist_ok=True)
    comp_path = os.path.join(args.output_dir, f"{args.track.lower()}_strategy_comparison.png")
    plot_strategy_comparison(base, opt, track, save_path=comp_path)

    print(f"\n[✓] Strategy comparison figure saved to: {comp_path}\n")


if __name__ == "__main__":
    main()
