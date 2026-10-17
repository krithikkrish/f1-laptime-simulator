"""
F1 2026 Transient Lap-Time & Hybrid Energy Deployment Simulator package.
"""

from .params import VehicleParams
from .track import Track, create_monza_track, create_silverstone_track, build_track_from_waypoints
from .aero import AeroModel, AeroMode
from .tire_model import TireModel, TireState
from .powertrain import Powertrain, PowertrainState
from .lts_engine import SimulationEngine, LapTelemetry
from .optimizer import DeploymentOptimizer, OptimizationResult
from .telemetry import (
    plot_telemetry_dashboard,
    plot_gg_diagram,
    plot_track_map,
    plot_strategy_comparison
)
from .vehicle_dynamics import DualTrackDynamics, FourWheelLoads, FourWheelGrip
from .transmission import SequentialTransmission, TransmissionState
from .setup_sheet import SetupSheet, HOMOLOGATED_PRESETS
from .motec_export import MoTecExporter, export_motec_csv, export_motec_ldx
from .openf1_client import OpenF1Client
from .physics_weather import WeatherConditions
from .tracks_data import create_calendar_track, get_available_circuits_list, find_canonical_circuit_key
from .pole_telemetry import get_real_pole_telemetry, get_pole_benchmark_info

__all__ = [
    "VehicleParams",
    "Track",
    "create_monza_track",
    "create_silverstone_track",
    "create_calendar_track",
    "get_available_circuits_list",
    "find_canonical_circuit_key",
    "build_track_from_waypoints",
    "AeroModel",
    "AeroMode",
    "TireModel",
    "TireState",
    "Powertrain",
    "PowertrainState",
    "SimulationEngine",
    "LapTelemetry",
    "DeploymentOptimizer",
    "OptimizationResult",
    "plot_telemetry_dashboard",
    "plot_gg_diagram",
    "plot_track_map",
    "plot_strategy_comparison",
    "DualTrackDynamics",
    "FourWheelLoads",
    "FourWheelGrip",
    "SequentialTransmission",
    "TransmissionState",
    "SetupSheet",
    "HOMOLOGATED_PRESETS",
    "MoTecExporter",
    "export_motec_csv",
    "export_motec_ldx",
    "OpenF1Client",
    "WeatherConditions",
    "get_real_pole_telemetry",
    "get_pole_benchmark_info",
]


