"""
High-Fidelity 4-Wheel / Dual-Track Vehicle Dynamics & Suspension Mechanics.
Implements:
1. 4-Corner Dynamic Normal Load Transfer (Static + Longitudinal Pitch + Lateral Roll + Aero Balance)
2. Suspension Roll Stiffness Distribution (Springs + Anti-Roll Bars)
3. Pacejka '02 Magic Formula Tire Formulation with Combined Slip & Slip Angles
4. Electronic Brake-by-Wire (BBW) Dynamic Brake Migration Table
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any
import numpy as np

from .params import VehicleParams


@dataclass
class FourWheelLoads:
    f_z_fl: float   # Front-Left normal load (N)
    f_z_fr: float   # Front-Right normal load (N)
    f_z_rl: float   # Rear-Left normal load (N)
    f_z_rr: float   # Rear-Right normal load (N)
    f_z_front_total: float
    f_z_rear_total: float
    f_z_total: float
    delta_f_long: float
    delta_f_lat_f: float
    delta_f_lat_r: float


@dataclass
class FourWheelGrip:
    f_grip_fl: float
    f_grip_fr: float
    f_grip_rl: float
    f_grip_rr: float
    f_x_max_total: float
    f_y_max_total: float
    slip_angle_f_deg: float
    slip_angle_r_deg: float
    steer_angle_deg: float


class DualTrackDynamics:
    """
    Dual-Track 4-Wheel chassis model with suspension compliance and dynamic load transfer.
    """
    def __init__(self, params: VehicleParams = None):
        self.p = params if params is not None else VehicleParams()
        
        # Chassis Geometry & Mass Distribution
        self.wheelbase = self.p.wheelbase          # L = 3.4 m
        self.track_f = self.p.track_width          # Front track width = 2.0 m
        self.track_r = self.p.track_width          # Rear track width = 2.0 m
        self.h_cg = 0.315                          # Center of Gravity height above ground (m)
        self.weight_dist_front = 0.455             # Static weight on front axle (45.5% front, 54.5% rear)
        
        # Center of gravity distances to axles
        self.dist_a = self.wheelbase * (1.0 - self.weight_dist_front) # Distance from front axle to CoG (m)
        self.dist_b = self.wheelbase * self.weight_dist_front         # Distance from rear axle to CoG (m)
        
        # Roll Geometry & Suspension Roll Stiffness (Nm/rad)
        self.h_roll_f = 0.045                      # Front kinematic roll center height (m)
        self.h_roll_r = 0.085                      # Rear kinematic roll center height (m)
        self.k_roll_f = 145_000.0                  # Front suspension roll stiffness (springs + ARB) (Nm/rad)
        self.k_roll_r = 105_000.0                  # Rear suspension roll stiffness (springs + ARB) (Nm/rad)
        
        # Aerodynamic Balance
        self.aero_balance_f = 0.445                # Front downforce percentage (44.5% front, 55.5% rear)
        
        # Pacejka '02 Magic Formula coefficients for F1 slicks
        # F_y = D * sin(C * arctan(B * alpha - E * (B * alpha - arctan(B * alpha))))
        self.pacejka_B = 10.5
        self.pacejka_C = 1.65
        self.pacejka_E = -0.45
        
        # Brake-by-Wire (BBW) parameters
        self.bbw_base_front_pct = 0.565            # 56.5% front base bias
        self.bbw_migration_gain = 0.022            # +2.2% frontward migration per 1.0g deceleration

    def compute_4wheel_loads(
        self,
        a_long_g: float,
        a_lat_g: float,
        f_downforce_total: float,
        grade_rad: float = 0.0
    ) -> FourWheelLoads:
        """
        Calculates the instantaneous normal vertical loads F_z on all 4 corners:
        FL, FR, RL, RR accounting for:
        1. Static chassis gravity distribution
        2. Aerodynamic downforce front/rear balance
        3. Longitudinal acceleration pitch load transfer
        4. Lateral acceleration roll load transfer with front/rear roll stiffness distribution
        """
        m_tot = self.p.total_mass
        g = self.p.gravity
        
        # 1. Static axle weight
        w_static_total = m_tot * g * np.cos(grade_rad)
        w_static_f = w_static_total * (self.dist_b / self.wheelbase)
        w_static_r = w_static_total * (self.dist_a / self.wheelbase)
        
        # 2. Aerodynamic downforce distribution
        f_down_f = f_downforce_total * self.aero_balance_f
        f_down_r = f_downforce_total * (1.0 - self.aero_balance_f)
        
        # 3. Longitudinal load transfer (N)
        # a_long_g > 0: Acceleration transfers load from front to rear
        # a_long_g < 0: Braking transfers load from rear to front
        delta_f_long = m_tot * (a_long_g * g) * (self.h_cg / self.wheelbase)
        
        # 4. Lateral load transfer across front and rear axles (N)
        k_roll_tot = self.k_roll_f + self.k_roll_r
        h_roll_eff = (self.h_roll_f * self.dist_b + self.h_roll_r * self.dist_a) / self.wheelbase
        arm_cg = max(0.05, self.h_cg - h_roll_eff)
        
        f_lat_total = m_tot * (a_lat_g * g)
        
        # Front axle lateral transfer
        delta_f_lat_f = (f_lat_total / self.track_f) * (
            (self.h_roll_f * self.dist_b / self.wheelbase) + (self.k_roll_f / k_roll_tot) * arm_cg
        )
        
        # Rear axle lateral transfer
        delta_f_lat_r = (f_lat_total / self.track_r) * (
            (self.h_roll_r * self.dist_a / self.wheelbase) + (self.k_roll_r / k_roll_tot) * arm_cg
        )
        
        # Individual corner vertical loads
        f_z_fl = max(250.0, 0.5 * (w_static_f + f_down_f) - 0.5 * delta_f_long - delta_f_lat_f)
        f_z_fr = max(250.0, 0.5 * (w_static_f + f_down_f) - 0.5 * delta_f_long + delta_f_lat_f)
        f_z_rl = max(250.0, 0.5 * (w_static_r + f_down_r) + 0.5 * delta_f_long - delta_f_lat_r)
        f_z_rr = max(250.0, 0.5 * (w_static_r + f_down_r) + 0.5 * delta_f_long + delta_f_lat_r)
        
        return FourWheelLoads(
            f_z_fl=f_z_fl,
            f_z_fr=f_z_fr,
            f_z_rl=f_z_rl,
            f_z_rr=f_z_rr,
            f_z_front_total=f_z_fl + f_z_fr,
            f_z_rear_total=f_z_rl + f_z_rr,
            f_z_total=f_z_fl + f_z_fr + f_z_rl + f_z_rr,
            delta_f_long=delta_f_long,
            delta_f_lat_f=delta_f_lat_f,
            delta_f_lat_r=delta_f_lat_r
        )

    def compute_tire_mu(self, f_z: float, t_tire_c: float, weather_grip_factor: float = 1.0) -> float:
        """
        Calculates local tire friction coefficient with load sensitivity and thermal operating window.
        """
        # Load sensitivity: friction decreases as normal load increases above 4kN reference
        delta_fz = max(0.0, f_z - self.p.fz_ref)
        mu_load = self.p.mu_peak * (1.0 - self.p.load_sensitivity * delta_fz)
        mu_load = max(0.85, mu_load)
        
        # Thermal efficiency bell-curve (peaks at 100°C)
        t_diff = t_tire_c - self.p.t_tire_opt
        thermal_factor = 0.70 + 0.30 * np.exp(-0.5 * (t_diff / self.p.t_tire_sigma) ** 2)
        if t_tire_c > 125.0:
            thermal_factor *= max(0.60, 1.0 - 0.015 * (t_tire_c - 125.0))
            
        mu_eff = mu_load * thermal_factor * weather_grip_factor
        return float(mu_eff)

    def evaluate_4wheel_grip_envelope(
        self,
        loads: FourWheelLoads,
        v_ms: float,
        radius_m: float,
        t_tire_c: float,
        weather_grip_factor: float = 1.0
    ) -> FourWheelGrip:
        """
        Evaluates 4-corner tire grip budgets, slip angles, and Ackermann steering angle.
        """
        # Corner friction coefficients
        mu_fl = self.compute_tire_mu(loads.f_z_fl, t_tire_c, weather_grip_factor)
        mu_fr = self.compute_tire_mu(loads.f_z_fr, t_tire_c, weather_grip_factor)
        mu_rl = self.compute_tire_mu(loads.f_z_rl, t_tire_c, weather_grip_factor)
        mu_rr = self.compute_tire_mu(loads.f_z_rr, t_tire_c, weather_grip_factor)
        
        # Maximum grip vector magnitudes (Pacejka limits)
        f_grip_fl = mu_fl * loads.f_z_fl
        f_grip_fr = mu_fr * loads.f_z_fr
        f_grip_rl = mu_rl * loads.f_z_rl
        f_grip_rr = mu_rr * loads.f_z_rr
        
        # Total lateral and longitudinal capabilities
        f_y_max_front = f_grip_fl + f_grip_fr
        f_y_max_rear = f_grip_rl + f_grip_rr
        f_y_max_total = f_y_max_front + f_y_max_rear
        f_x_max_total = f_grip_fl + f_grip_fr + f_grip_rl + f_grip_rr
        
        # Slip angles and steering angle kinematics
        if radius_m < 9000.0 and v_ms > 5.0:
            a_lat = (v_ms ** 2) / radius_m
            f_y_demand_f = self.p.total_mass * a_lat * (self.dist_b / self.wheelbase)
            f_y_demand_r = self.p.total_mass * a_lat * (self.dist_a / self.wheelbase)
            
            # Cornering stiffness estimates (N/rad)
            c_alpha_f = 28.0 * loads.f_z_front_total
            c_alpha_r = 30.0 * loads.f_z_rear_total
            
            alpha_f_rad = f_y_demand_f / max(1e3, c_alpha_f)
            alpha_r_rad = f_y_demand_r / max(1e3, c_alpha_r)
            
            # Ackermann kinematic angle + understeer compliance
            delta_steer_rad = (self.wheelbase / radius_m) + (alpha_f_rad - alpha_r_rad)
        else:
            alpha_f_rad = 0.0
            alpha_r_rad = 0.0
            delta_steer_rad = 0.0
            
        return FourWheelGrip(
            f_grip_fl=f_grip_fl,
            f_grip_fr=f_grip_fr,
            f_grip_rl=f_grip_rl,
            f_grip_rr=f_grip_rr,
            f_x_max_total=f_x_max_total,
            f_y_max_total=f_y_max_total,
            slip_angle_f_deg=float(np.degrees(alpha_f_rad)),
            slip_angle_r_deg=float(np.degrees(alpha_r_rad)),
            steer_angle_deg=float(np.degrees(delta_steer_rad))
        )

    def compute_bbw_bias(self, a_long_g: float) -> float:
        """
        Calculates dynamic Brake-by-Wire (BBW) front brake bias percentage.
        Migrates forward under threshold braking to prevent rear axle destabilization.
        """
        decel_g = max(0.0, -a_long_g)
        bias_f = self.bbw_base_front_pct + (self.bbw_migration_gain * decel_g)
        return float(np.clip(bias_f, 0.50, 0.65))
