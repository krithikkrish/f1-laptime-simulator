"""
F1 2026 Hybrid Powertrain Module:
1. Internal Combustion Engine (ICE, 400 kW sustainable V6 Turbo)
2. Motor Generator Unit - Kinetic (MGU-K, 350 kW) with FIA 2026 >290 km/h power tapering
3. Energy Storage System (ESS) State of Charge (SoC) integration ODE
4. Brake-by-wire regenerative harvest vs mechanical friction blending
"""

from dataclasses import dataclass
import numpy as np
from .params import VehicleParams


@dataclass
class PowertrainState:
    p_ice: float             # ICE mechanical power output (Watts)
    p_mguk_deploy: float     # MGU-K electrical deployment power (Watts)
    p_mguk_regen: float      # MGU-K regenerative harvest power (Watts)
    p_total_drive: float     # Total combined driving power (Watts)
    f_drive: float           # Longitudinal drive force generated at wheels (N)
    f_brake_regen: float     # Regenerative retarding force at wheels (N)
    f_brake_mech: float      # Mechanical disc brake retarding force (N)
    f_brake_total: float     # Total retarding force (N)
    soc_joules: float        # Battery stored energy (Joules)
    soc_fraction: float      # State of charge 0.0 to 1.0 (dimensionless)
    p_mguk_allowed_cap: float# Current speed-dependent 2026 FIA MGU-K cap (Watts)


class Powertrain:
    def __init__(self, params: VehicleParams):
        self.p = params
        self.soc_joules = params.battery_capacity_joules * params.soc_initial
        self.lap_energy_deployed_joules = 0.0
        self.lap_energy_harvested_joules = 0.0

    def reset(self, initial_soc_fraction: float = None):
        frac = initial_soc_fraction if initial_soc_fraction is not None else self.p.soc_initial
        self.soc_joules = self.p.battery_capacity_joules * np.clip(frac, 0.05, 0.98)
        self.lap_energy_deployed_joules = 0.0
        self.lap_energy_harvested_joules = 0.0

    def get_mguk_tapered_cap(self, v_ms: float) -> float:
        """
        2026 FIA Regulation Tapering Curve:
        - Speed <= 290 km/h: Full 350 kW available
        - 290 km/h < Speed <= 345 km/h: Linear taper from 350 kW down to 0 kW
        - Speed > 345 km/h: 0 kW electrical boost
        """
        v_start = self.p.v_taper_start_ms
        v_end = self.p.v_taper_end_ms

        if v_ms <= v_start:
            return self.p.p_mguk_deploy_max
        elif v_ms >= v_end:
            return 0.0
        else:
            slope = (v_ms - v_start) / (v_end - v_start)
            return self.p.p_mguk_deploy_max * max(0.0, 1.0 - slope)

    def compute_drive_forces(self, v_ms: float, throttle: float, deploy_factor: float, f_x_grip_limit: float) -> PowertrainState:
        """
        Calculates drive power and wheel tractive force under acceleration.
        Enforces:
        - 2026 MGU-K 350kW cap with speed tapering
        - Battery minimum SoC floor (5%)
        - Traction grip envelope
        """
        v_effective = max(v_ms, 3.5)  # Avoid division by zero at standstill (clutch slip model)
        soc_frac = self.soc_joules / self.p.battery_capacity_joules

        # 1. ICE Power delivery (proportional to throttle)
        p_ice = self.p.p_ice_max * np.clip(throttle, 0.0, 1.0)

        # 2. MGU-K Deployment delivery
        p_allowed_cap = self.get_mguk_tapered_cap(v_ms)

        if soc_frac <= self.p.soc_min_safe or throttle <= 0.05:
            p_mguk_deploy = 0.0
        else:
            # Scale by throttle, optimizer deployment factor, and speed taper
            p_demand = self.p.p_mguk_deploy_max * np.clip(deploy_factor, 0.0, 1.0) * throttle
            p_mguk_deploy = min(p_demand, p_allowed_cap)

            # Check if energy request would violate 5% floor in a 0.1s horizon
            energy_headroom = max(0.0, self.soc_joules - (self.p.soc_min_safe * self.p.battery_capacity_joules))
            p_max_safe = (energy_headroom / 0.1) * self.p.eta_deploy
            p_mguk_deploy = min(p_mguk_deploy, p_max_safe)

        # Total combined driving power
        p_total = p_ice + p_mguk_deploy

        # Tractive force at contact patch F = P / v
        f_drive_raw = p_total / v_effective

        # Clamp against available longitudinal tire traction limit
        f_drive = min(f_drive_raw, f_x_grip_limit)

        return PowertrainState(
            p_ice=p_ice,
            p_mguk_deploy=p_mguk_deploy,
            p_mguk_regen=0.0,
            p_total_drive=p_total,
            f_drive=f_drive,
            f_brake_regen=0.0,
            f_brake_mech=0.0,
            f_brake_total=0.0,
            soc_joules=self.soc_joules,
            soc_fraction=soc_frac,
            p_mguk_allowed_cap=p_allowed_cap
        )

    def compute_braking_forces(self, v_ms: float, brake_demand_n: float, f_x_grip_limit: float) -> PowertrainState:
        """
        Brake-by-wire system: Blends MGU-K regenerative braking up to 350kW with mechanical disc brakes.
        """
        v_effective = max(v_ms, 1.0)
        soc_frac = self.soc_joules / self.p.battery_capacity_joules

        # Target deceleration force bounded by tire grip
        f_brake_target = min(brake_demand_n, f_x_grip_limit)
        p_brake_total = f_brake_target * v_effective

        # Regenerative braking allocation (MGU-K harvests up to 350 kW)
        if soc_frac >= self.p.soc_max_safe or v_ms < 5.0:
            p_regen = 0.0
        else:
            p_regen = min(p_brake_total, self.p.p_mguk_regen_max)

        f_brake_regen = p_regen / v_effective if v_effective > 0.0 else 0.0
        f_brake_mech = max(0.0, f_brake_target - f_brake_regen)

        return PowertrainState(
            p_ice=0.0,
            p_mguk_deploy=0.0,
            p_mguk_regen=p_regen,
            p_total_drive=0.0,
            f_drive=0.0,
            f_brake_regen=f_brake_regen,
            f_brake_mech=f_brake_mech,
            f_brake_total=f_brake_target,
            soc_joules=self.soc_joules,
            soc_fraction=soc_frac,
            p_mguk_allowed_cap=self.get_mguk_tapered_cap(v_ms)
        )

    def step_soc_ode(self, p_deploy: float, p_regen: float, dt: float) -> float:
        """
        Integrates State of Charge ODE:
        d(SoC)/dt = P_regen * eta_regen - P_deploy / eta_deploy
        """
        d_soc_dt = (p_regen * self.p.eta_regen) - (p_deploy / self.p.eta_deploy)
        self.soc_joules += d_soc_dt * dt

        # Accumulate metrics
        self.lap_energy_deployed_joules += (p_deploy * dt)
        self.lap_energy_harvested_joules += (p_regen * dt)

        # Clamp between 0 and maximum battery capacity
        self.soc_joules = np.clip(self.soc_joules, 0.0, self.p.battery_capacity_joules)
        return self.soc_joules
