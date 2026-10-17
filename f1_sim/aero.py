"""
2026 Active Aerodynamics (X-Mode & Z-Mode) Simulation Module.
Computes aerodynamic downforce and drag based on velocity and aero mode.
"""

from enum import Enum
from dataclasses import dataclass
from .params import VehicleParams


class AeroMode(Enum):
    Z_MODE = "Z-Mode (High Downforce)"
    X_MODE = "X-Mode (Low Drag)"


@dataclass
class AeroState:
    mode: AeroMode
    f_downforce: float   # Newtons
    f_drag: float        # Newtons
    cl_A: float          # m^2
    cd_A: float          # m^2


class AeroModel:
    def __init__(self, params: VehicleParams):
        self.p = params

    def determine_mode(self, v: float, a_lat: float, is_corner: bool, brake_input: float = 0.0) -> AeroMode:
        """
        Active Aero Decision Logic:
        - Z-Mode active during cornering (a_lat > 0.8g), heavy braking (> 0.2), or inside marked corner zones.
        - X-Mode activates on straights once the car is accelerating and lateral demand drops.
        """
        if is_corner or abs(a_lat) > 8.0 or brake_input > 0.15 or v < 25.0:
            return AeroMode.Z_MODE
        return AeroMode.X_MODE

    def calculate_forces(self, v: float, mode: AeroMode) -> AeroState:
        """
        Calculates downforce F_down = 0.5 * rho * ClA * v^2
        and drag F_drag = 0.5 * rho * CdA * v^2
        """
        if mode == AeroMode.Z_MODE:
            cl_A = self.p.cl_A_z_mode
            cd_A = self.p.cd_A_z_mode
        else:
            cl_A = self.p.cl_A_x_mode
            cd_A = self.p.cd_A_x_mode

        q = 0.5 * self.p.air_density * (v ** 2)
        f_down = q * cl_A
        f_drag = q * cd_A

        return AeroState(
            mode=mode,
            f_downforce=f_down,
            f_drag=f_drag,
            cl_A=cl_A,
            cd_A=cd_A
        )
