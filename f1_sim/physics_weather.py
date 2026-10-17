"""
Atmospheric, meteorological, and environmental physics engine for F1 Lap Time Simulation.
Calculates dynamic air density rho(p, T, rh), relative wind vector velocity,
track temperature grip scaling, and rain surface degradation.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class WeatherConditions:
    air_temp_c: float = 25.0           # Ambient air temperature (°C)
    track_temp_c: float = 38.0         # Asphalt track temperature (°C)
    humidity_pct: float = 50.0         # Relative humidity (%)
    pressure_hpa: float = 1013.25      # Atmospheric air pressure (hPa = mbar)
    wind_speed_ms: float = 2.0         # Wind velocity (m/s)
    wind_dir_deg: float = 90.0         # Meteorological wind direction (degrees, 0=N, 90=E, 180=S, 270=W)
    rainfall: int = 0                  # 0: Dry, 1: Damp/Wet

    @property
    def air_temp_k(self) -> float:
        return self.air_temp_c + 273.15

    @property
    def air_density(self) -> float:
        """
        Computes humid air density (kg/m^3) using the CIPM-2007 approximation.
        Accounts for barometric altitude and water vapor partial pressure.
        """
        p_pa = self.pressure_hpa * 100.0  # hPa to Pa
        T_k = self.air_temp_k

        # Saturated vapor pressure (Magnus-Tetens formula)
        p_sat = 610.78 * np.exp((17.27 * self.air_temp_c) / (self.air_temp_c + 237.3))
        # Actual vapor pressure
        p_v = (self.humidity_pct / 100.0) * p_sat
        # Partial pressure of dry air
        p_d = max(1000.0, p_pa - p_v)

        # Gas constants
        R_d = 287.058  # J/(kg·K) for dry air
        R_v = 461.495  # J/(kg·K) for water vapor

        rho = (p_d / (R_d * T_k)) + (p_v / (R_v * T_k))
        return float(np.clip(rho, 0.80, 1.45))

    def compute_track_grip_factor(self, compound_type: str = "SLICK") -> float:
        """
        Computes asphalt surface grip multiplier based on track temperature and rainfall.
        Slick tires have optimal operating friction between 30°C and 45°C asphalt.
        """
        if self.rainfall > 0 and compound_type == "SLICK":
            return 0.65  # Severe aquaplaning/loss of grip on wet track with slicks

        # Track temperature influence on slick adhesion
        # Optimal asphalt window: 32°C - 44°C
        T = self.track_temp_c
        if 32.0 <= T <= 44.0:
            grip_t = 1.0
        elif T < 32.0:
            # Cold track reduces adhesion, increases graining
            delta = 32.0 - T
            grip_t = 1.0 - 0.0035 * delta - 0.00015 * (delta ** 2)
        else:
            # Scorching track accelerates blistering and thermal softening
            delta = T - 44.0
            grip_t = 1.0 - 0.0025 * delta - 0.00010 * (delta ** 2)

        return float(np.clip(grip_t, 0.75, 1.05))

    def compute_relative_air_velocity(self, v_car: float, track_heading_rad: float) -> float:
        """
        Computes the effective aerodynamic airspeed v_aero experienced by the car:
        v_aero = v_car - v_wind * cos(heading - wind_dir)
        A headwind increases aero dynamic pressure; a tailwind reduces it.
        """
        # Convert meteorological wind direction (direction wind is blowing from) to math radians
        wind_rad = np.radians(self.wind_dir_deg)
        # Angle difference between car travel vector and wind vector
        angle_diff = track_heading_rad - wind_rad
        headwind_component = self.wind_speed_ms * np.cos(angle_diff)
        
        # Effective airspeed
        v_aero = v_car + headwind_component
        return float(max(0.0, v_aero))
