"""
F1 2026 Technical Regulations & Vehicle Dynamics Parameter Specifications.
Covers Powertrain (ICE + 350kW MGU-K), Active Aerodynamics (Z-Mode & X-Mode),
Thermal Tire Model, and Energy Storage (ES).
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class VehicleParams:
    # Mass Properties
    mass_empty: float = 768.0       # 2026 FIA minimum car mass (kg)
    mass_driver: float = 80.0       # Driver + seat ballast standard (kg)
    fuel_mass: float = 40.0         # Qualifying / Sprint fuel load (kg)
    
    @property
    def total_mass(self) -> float:
        return self.mass_empty + self.mass_driver + self.fuel_mass

    # Physical Dimensions & Environment
    wheelbase: float = 3.4          # Meters
    track_width: float = 2.0        # Meters
    gravity: float = 9.80665        # m/s^2
    air_density: float = 1.225      # kg/m^3 at sea level, 20°C
    ambient_temp: float = 25.0      # °C
    
    # Active Aerodynamics (2026 Spec: Z-Mode for Cornering, X-Mode for Straights)
    # Z-Mode (High Downforce): Active in cornering / heavy braking
    cd_A_z_mode: float = 1.15       # Drag area (m^2)
    cl_A_z_mode: float = 3.20       # Downforce area (m^2)
    
    # X-Mode (Low Drag / Straight Mode): Active on straights above corner exit
    cd_A_x_mode: float = 0.65       # Drag area (m^2)
    cl_A_x_mode: float = 1.10       # Downforce area (m^2)
    
    # Rolling Resistance
    c_rr: float = 0.015             # Dimensionless rolling resistance coefficient

    # Powertrain - Internal Combustion Engine (ICE)
    p_ice_max: float = 400_000.0    # 400 kW (~536 bhp) sustainable fuel 1.6L V6 Turbo

    # Powertrain - Motor Generator Unit - Kinetic (MGU-K) 2026 Specs
    p_mguk_deploy_max: float = 350_000.0   # 350 kW maximum electrical deployment
    p_mguk_regen_max: float = 350_000.0    # 350 kW maximum braking regeneration
    
    # 2026 FIA MGU-K Power Tapering Curve
    # Full 350 kW available up to 290 km/h (80.56 m/s), tapering to 0 kW at 345 km/h (95.83 m/s)
    v_taper_start_kmh: float = 290.0
    v_taper_end_kmh: float = 345.0
    
    @property
    def v_taper_start_ms(self) -> float:
        return self.v_taper_start_kmh / 3.6

    @property
    def v_taper_end_ms(self) -> float:
        return self.v_taper_end_kmh / 3.6

    # Energy Storage (ES) / Battery
    battery_capacity_joules: float = 8.5e6  # 8.5 MJ total capacity (~2.36 kWh)
    usable_lap_energy_joules: float = 4.0e6 # 4.0 MJ maximum net deployment allowance per lap
    soc_initial: float = 0.65              # 65% initial SoC
    soc_min_safe: float = 0.05             # 5% minimum emergency floor
    soc_max_safe: float = 0.98             # 98% upper limit
    eta_deploy: float = 0.94               # Inverter + Motor electrical efficiency
    eta_regen: float = 0.90                # Inverter + Generator recovery efficiency

    # Mechanical Braking System (Carbon-Carbon discs, strictly tire-grip limited)
    f_brake_max_mechanical: float = 65_000.0 # Newtons max mechanical disc braking capacity

    # Tire Mechanics & Thermal Model
    tire_compound: str = "SLICK"           # "SLICK", "INTERMEDIATE", "WET"
    mu_peak: float = 1.72                  # Peak friction coefficient at optimum temp and reference load
    fz_ref: float = 4_000.0                # Reference normal load per axle or corner (N)
    load_sensitivity: float = 0.000030     # 1/N load sensitivity factor
    
    t_tire_opt: float = 100.0              # Optimum carcass/tread bulk temp (°C)
    t_tire_sigma: float = 25.0             # Temperature window spread (°C)
    t_tire_initial: float = 90.0           # Starting tire temp out of warmers (°C)
    t_tire_critical: float = 135.0         # Overheating blistering threshold (°C)
    
    # Tire Thermal Dynamics: dT/dt = (Q_gen - Q_cool) / C_thermal
    c_tire_thermal: float = 1800.0         # Thermal mass capacity (J/K)
    h_cool_base: float = 20.0              # Base convective cooling (W/K)
    h_cool_speed_gain: float = 0.65        # Cooling gain with velocity (W/(K * m/s))
    k_heat_gen_slip: float = 0.045         # Friction heat generation coefficient from tractive/cornering power

    # Simulation Integration
    dt: float = 0.01                       # Forward-Euler time-stepping interval (seconds)
