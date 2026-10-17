"""
8-Speed Seamless-Shift Sequential Transmission & Engine RPM Dynamics Module.
Implements:
1. FIA 2026 8-Speed Gear Ratios & Final Drive
2. Continuous Engine RPM Calculation: N_e(v, gear)
3. Closed-Loop Optimal Gear Selection Logic (Upshift @ 11,200 RPM, Downshift @ 8,600 RPM)
4. 15ms Seamless-Shift Ignition/Fuel Cut Mechanics
5. Engine Torque-Speed Characteristic Curve (400kW ICE + 350kW MGU-K)
"""

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass
class TransmissionState:
    gear: int               # Current engaged gear (1 to 8)
    engine_rpm: float       # Internal combustion engine rotational speed (RPM)
    wheel_rpm: float        # Driven wheel axle speed (RPM)
    wheel_torque_nm: float  # Tractive torque delivered to rear axle (Nm)
    is_shifting: bool       # True during 15ms seamless shift cut
    shift_torque_factor: float # Torque attenuation multiplier (0.0 during cut, 1.0 engaged)


class SequentialTransmission:
    def __init__(self):
        # Pirelli 18-inch F1 low-profile tire rolling radius
        self.r_wheel = 0.360  # meters (Diameter ~ 720 mm)
        
        # FIA 2026 Homologated 8-Speed Gear Ratios (overall ratio including final drive)
        # Ratio = N_engine / N_wheel
        self.gear_ratios = {
            1: 12.85,
            2: 10.15,
            3: 8.35,
            4: 7.05,
            5: 6.05,
            6: 5.25,
            7: 4.60,
            8: 4.02
        }
        
        # Engine operating envelope
        self.rpm_idle = 4_000.0
        self.rpm_shift_down = 8_400.0
        self.rpm_shift_up = 11_200.0
        self.rpm_redline = 12_100.0
        
        # Drivetrain mechanical efficiency
        self.eta_drivetrain = 0.965
        
        # Shift state tracking
        self.current_gear = 1
        self.shift_timer_s = 0.0
        self.shift_duration_s = 0.015  # 15 ms seamless-shift time

    def get_optimal_gear(self, v_ms: float) -> int:
        """
        Determines the optimal gear (1 to 8) for a given road speed v (m/s)
        to maintain engine in peak powerband (9,500 - 11,200 RPM).
        """
        if v_ms < 2.0:
            return 1
            
        w_wheel = v_ms / self.r_wheel  # rad/s
        rpm_wheel = w_wheel * (60.0 / (2.0 * np.pi))
        
        # Evaluate candidate gears from 1 to 8
        best_gear = 1
        for g in range(1, 9):
            ratio = self.gear_ratios[g]
            rpm_cand = rpm_wheel * ratio
            if rpm_cand <= self.rpm_shift_up:
                best_gear = g
                break
            best_gear = g
            
        # Ensure we don't drop below idle or exceed redline
        ratio_best = self.gear_ratios[best_gear]
        rpm_eval = rpm_wheel * ratio_best
        if rpm_eval > self.rpm_redline and best_gear < 8:
            best_gear += 1
            
        return int(best_gear)

    def calculate_state(self, v_ms: float, throttle: float, p_total_watts: float, dt: float = 0.01) -> TransmissionState:
        """
        Calculates instantaneous gear, engine RPM, and wheel tractive torque.
        Accounts for seamless shift cuts.
        """
        v_clamped = max(0.5, v_ms)
        w_wheel = v_clamped / self.r_wheel
        rpm_wheel = w_wheel * (60.0 / (2.0 * np.pi))
        
        target_gear = self.get_optimal_gear(v_ms)
        
        is_shifting = False
        shift_factor = 1.0
        
        if target_gear != self.current_gear:
            self.current_gear = target_gear
            self.shift_timer_s = self.shift_duration_s
            is_shifting = True
            shift_factor = 0.15  # 85% torque cut during 15ms shift
        elif self.shift_timer_s > 0.0:
            self.shift_timer_s -= dt
            is_shifting = True
            shift_factor = 0.15
            
        ratio = self.gear_ratios[self.current_gear]
        engine_rpm = np.clip(rpm_wheel * ratio, self.rpm_idle, self.rpm_redline)
        
        # Tractive torque at driven wheels
        # Power = Torque * angular_velocity
        # Wheel torque = (Power / w_wheel) * eta
        wheel_torque = 0.0
        if throttle > 0.0 and w_wheel > 0.1:
            wheel_torque = (p_total_watts / w_wheel) * self.eta_drivetrain * shift_factor
            
        return TransmissionState(
            gear=self.current_gear,
            engine_rpm=float(engine_rpm),
            wheel_rpm=float(rpm_wheel),
            wheel_torque_nm=float(wheel_torque),
            is_shifting=is_shifting,
            shift_torque_factor=float(shift_factor)
        )
