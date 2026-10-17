"""
Motorsport Engineering Setup Sheet & Setup A/B Comparison Engine.
Provides complete race engineer vehicle configuration presets:
- Aerodynamic wing trims, aero balance, active aero trims
- Suspension spring rates, anti-roll bars (ARB), ride heights
- Brake bias baseline and dynamic deceleration migration
- Powertrain MGU-K curves and tire compound configurations
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List
import copy

from .params import VehicleParams


@dataclass
class SetupSheet:
    name: str = "Standard 2026 Spec"
    description: str = "FIA 2026 Baseline Reference Setup"
    
    # Aerodynamics Setup
    front_wing_flap_deg: float = 24.0          # Front wing flap inclination angle (deg)
    rear_wing_beam_deg: float = 32.0           # Rear wing mainplane angle (deg)
    aero_balance_front_pct: float = 44.5       # Front downforce percentage (%)
    cl_a_z_mode: float = 3.20                  # Z-Mode cornering downforce area (m^2)
    cd_a_z_mode: float = 1.15                  # Z-Mode cornering drag area (m^2)
    cl_a_x_mode: float = 1.10                  # X-Mode straight downforce area (m^2)
    cd_a_x_mode: float = 0.65                  # X-Mode straight low-drag area (m^2)
    
    # Mechanical Suspension Setup
    front_spring_rate_n_mm: float = 160.0      # Front wheel rate / spring stiffness (N/mm)
    rear_spring_rate_n_mm: float = 110.0       # Rear wheel rate / spring stiffness (N/mm)
    front_arb_stiffness_n_mm: float = 340.0    # Front Anti-Roll Bar stiffness (N/mm)
    rear_arb_stiffness_n_mm: float = 180.0     # Rear Anti-Roll Bar stiffness (N/mm)
    front_ride_height_mm: float = 28.0         # Static front ride height (mm)
    rear_ride_height_mm: float = 48.0          # Static rear ride height (mm)
    
    # Braking System & BBW
    brake_bias_front_pct: float = 56.5         # Baseline static front brake bias (%)
    brake_migration_gain: float = 0.022        # Forward migration gain per g deceleration
    brake_disc_diameter_mm: float = 330.0      # Carbon-carbon disc diameter (mm)
    
    # Powertrain & Energy Storage
    ice_power_kw: float = 400.0                # 1.6L V6 Turbo engine power (kW)
    mguk_power_kw: float = 350.0               # 2026 MGU-K electric motor power (kW)
    mguk_taper_start_kmh: float = 290.0        # MGU-K tapering start threshold (km/h)
    mguk_taper_end_kmh: float = 345.0          # MGU-K electrical cutoff speed (km/h)
    initial_soc_pct: float = 65.0              # Initial battery state of charge (%)
    
    # Chassis & Tires
    car_empty_mass_kg: float = 768.0           # Minimum vehicle mass (kg)
    fuel_load_kg: float = 40.0                 # Fuel mass on board (kg)
    front_weight_dist_pct: float = 45.5        # Static front weight distribution (%)
    tire_compound: str = "Soft Slick (C5)"     # Tire compound designation
    tire_warmer_temp_c: float = 90.0           # Tire blanket preheat temperature (°C)
    peak_friction_mu: float = 1.76             # Peak friction coefficient

    def to_vehicle_params(self) -> VehicleParams:
        """Converts this engineering setup sheet into a typed VehicleParams model."""
        return VehicleParams(
            mass_empty=self.car_empty_mass_kg,
            fuel_mass=self.fuel_load_kg,
            p_ice_max=self.ice_power_kw * 1e3,
            p_mguk_deploy_max=self.mguk_power_kw * 1e3,
            p_mguk_regen_max=self.mguk_power_kw * 1e3,
            v_taper_start_kmh=self.mguk_taper_start_kmh,
            v_taper_end_kmh=self.mguk_taper_end_kmh,
            cl_A_z_mode=self.cl_a_z_mode,
            cd_A_z_mode=self.cd_a_z_mode,
            cl_A_x_mode=self.cl_a_x_mode,
            cd_A_x_mode=self.cd_a_x_mode,
            mu_peak=self.peak_friction_mu,
            t_tire_initial=self.tire_warmer_temp_c,
            tire_compound="WET" if ("Wet" in self.tire_compound or "Inter" in self.tire_compound) else "SLICK"
        )


# Pre-configured Official Motorsport Setup Profiles
PRESET_MONZA_LOW_DRAG = SetupSheet(
    name="Monza Low-Drag Spec",
    description="Optimized for maximum top speed (350+ km/h), minimal wing trim, stiff anti-roll bars",
    front_wing_flap_deg=16.0,
    rear_wing_beam_deg=20.0,
    aero_balance_front_pct=42.5,
    cl_a_z_mode=2.50,
    cd_a_z_mode=0.92,
    cl_a_x_mode=0.85,
    cd_a_x_mode=0.52,
    front_spring_rate_n_mm=180.0,
    rear_spring_rate_n_mm=125.0,
    front_arb_stiffness_n_mm=380.0,
    rear_arb_stiffness_n_mm=210.0,
    front_ride_height_mm=25.0,
    rear_ride_height_mm=42.0,
    brake_bias_front_pct=57.0,
    ice_power_kw=405.0,
    mguk_power_kw=350.0,
    mguk_taper_start_kmh=295.0,
    mguk_taper_end_kmh=350.0,
    tire_compound="Medium Slick (C3)",
    peak_friction_mu=1.70
)

PRESET_HIGH_DOWNFORCE = SetupSheet(
    name="High-Downforce Monaco Spec",
    description="Maximum cornering adhesion and aerodynamic grip for tight and twisty circuits",
    front_wing_flap_deg=34.0,
    rear_wing_beam_deg=44.0,
    aero_balance_front_pct=46.5,
    cl_a_z_mode=3.85,
    cd_a_z_mode=1.35,
    cl_a_x_mode=1.45,
    cd_a_x_mode=0.78,
    front_spring_rate_n_mm=135.0,
    rear_spring_rate_n_mm=95.0,
    front_arb_stiffness_n_mm=290.0,
    rear_arb_stiffness_n_mm=150.0,
    front_ride_height_mm=32.0,
    rear_ride_height_mm=54.0,
    brake_bias_front_pct=55.0,
    ice_power_kw=400.0,
    mguk_power_kw=350.0,
    mguk_taper_start_kmh=285.0,
    mguk_taper_end_kmh=340.0,
    tire_compound="Soft Slick (C5)",
    peak_friction_mu=1.78
)

PRESET_BALANCED_RACE = SetupSheet(
    name="Balanced Grand Prix Spec",
    description="Optimal compromise between straightline speed and high-speed aerodynamic stability",
    front_wing_flap_deg=25.0,
    rear_wing_beam_deg=32.0,
    aero_balance_front_pct=44.5,
    cl_a_z_mode=3.20,
    cd_a_z_mode=1.15,
    cl_a_x_mode=1.10,
    cd_a_x_mode=0.65,
    front_spring_rate_n_mm=160.0,
    rear_spring_rate_n_mm=110.0,
    front_arb_stiffness_n_mm=340.0,
    rear_arb_stiffness_n_mm=180.0,
    front_ride_height_mm=28.0,
    rear_ride_height_mm=48.0,
    brake_bias_front_pct=56.5,
    ice_power_kw=400.0,
    mguk_power_kw=350.0,
    mguk_taper_start_kmh=290.0,
    mguk_taper_end_kmh=345.0,
    tire_compound="Soft Slick (C5)",
    peak_friction_mu=1.76
)

PRESET_WET_WEATHER = SetupSheet(
    name="Wet-Weather Spec",
    description="Soft suspension compliance, raised ride height to clear puddles, and forward brake bias",
    front_wing_flap_deg=28.0,
    rear_wing_beam_deg=36.0,
    aero_balance_front_pct=45.0,
    cl_a_z_mode=3.40,
    cd_a_z_mode=1.25,
    cl_a_x_mode=1.20,
    cd_a_x_mode=0.72,
    front_spring_rate_n_mm=120.0,
    rear_spring_rate_n_mm=85.0,
    front_arb_stiffness_n_mm=220.0,
    rear_arb_stiffness_n_mm=120.0,
    front_ride_height_mm=38.0,
    rear_ride_height_mm=60.0,
    brake_bias_front_pct=59.0,
    ice_power_kw=380.0,
    mguk_power_kw=300.0,
    mguk_taper_start_kmh=280.0,
    mguk_taper_end_kmh=335.0,
    tire_compound="Full Wet",
    peak_friction_mu=1.25
)

SETUP_PRESETS: Dict[str, SetupSheet] = {
    "Balanced Grand Prix Spec": PRESET_BALANCED_RACE,
    "Monza Low-Drag Spec": PRESET_MONZA_LOW_DRAG,
    "High-Downforce Monaco Spec": PRESET_HIGH_DOWNFORCE,
    "Wet-Weather Spec": PRESET_WET_WEATHER
}

HOMOLOGATED_PRESETS = SETUP_PRESETS

