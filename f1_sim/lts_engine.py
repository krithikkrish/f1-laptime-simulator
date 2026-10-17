"""
Transient Lap-Time Simulation (LTS) Numerical Integration Engine.
Combines:
1. Spatial Forward-Backward Apex Solver (Optimal Racing Line Velocity Target)
2. High-Fidelity Forward-Euler 0.01s Time-Stepping ODE Loop:
   - Longitudinal Newton Mechanics
   - Active Aerodynamics (Z-Mode vs X-Mode)
   - Dynamic Slip & Thermal Tire Model
   - 2026 MGU-K (350kW) Hybrid Energy Storage (SoC) Integration
"""

from dataclasses import dataclass
import numpy as np
from scipy.interpolate import interp1d

from .params import VehicleParams
from .track import Track
from .aero import AeroModel, AeroMode
from .tire_model import TireModel
from .powertrain import Powertrain
from .physics_weather import WeatherConditions
from .vehicle_dynamics import DualTrackDynamics, FourWheelLoads
from .transmission import SequentialTransmission, TransmissionState


@dataclass
class LapTelemetry:
    lap_time: float
    distance_total: float
    time: np.ndarray
    s: np.ndarray
    v: np.ndarray
    v_kmh: np.ndarray
    a_x: np.ndarray
    a_y: np.ndarray
    throttle: np.ndarray
    brake: np.ndarray
    p_ice_kw: np.ndarray
    p_mguk_kw: np.ndarray
    soc_percent: np.ndarray
    t_tire_c: np.ndarray
    mu_eff: np.ndarray
    f_downforce_n: np.ndarray
    f_drag_n: np.ndarray
    aero_mode: np.ndarray
    net_energy_deployed_mj: float
    net_energy_harvested_mj: float
    delta_soc_percent: float
    gear: np.ndarray = None
    engine_rpm: np.ndarray = None
    steering_angle_deg: np.ndarray = None
    f_z_fl: np.ndarray = None
    f_z_fr: np.ndarray = None
    f_z_rl: np.ndarray = None
    f_z_rr: np.ndarray = None
    bbw_front_pct: np.ndarray = None


class SimulationEngine:
    def __init__(self, params: VehicleParams = None, weather: WeatherConditions = None):
        self.p = params if params is not None else VehicleParams()
        self.weather = weather if weather is not None else WeatherConditions()
        self.aero = AeroModel(self.p)
        self.tire = TireModel(self.p)
        self.powertrain = Powertrain(self.p)
        self.dual_track = DualTrackDynamics(self.p)
        self.transmission = SequentialTransmission()

    def solve_cornering_speed_envelope(self, track: Track, weather: WeatherConditions = None) -> np.ndarray:
        """
        Solves analytical maximum cornering speed at every track point s:
        a_lat = v^2 / R <= mu * Fz / M
        M * v^2 / R <= mu * (M * g * cos(theta) + 0.5 * rho * ClA * v^2)
        v_max = sqrt( (mu * g * cos(theta)) / (1/R - (0.5 * rho * ClA * mu) / M) )
        """
        w = weather if weather is not None else self.weather
        rho = w.air_density
        grip_factor = w.compute_track_grip_factor(getattr(self.p, "tire_compound", "SLICK"))

        n_pts = len(track.s)
        v_corner_limit = np.zeros(n_pts)
        cl_A = self.p.cl_A_z_mode  # High downforce active in corners

        # Effective tire peak friction incorporating real-world track conditions
        mu_nom = self.p.mu_peak * 0.95 * grip_factor

        for i in range(n_pts):
            R = track.corner_radius[i]
            theta = np.arcsin(np.clip(track.grade[i], -0.2, 0.2))
            g_eff = self.p.gravity * np.cos(theta)

            denom = (1.0 / R) - (0.5 * rho * cl_A * mu_nom / self.p.total_mass)
            if denom <= 0:
                # Aero downforce outstrips centrifugal requirement; limited only by drag/power
                v_corner_limit[i] = 100.0  # 360 km/h ceiling
            else:
                v_corner_limit[i] = np.sqrt((mu_nom * g_eff) / denom)

            # Cap at 360 km/h
            v_corner_limit[i] = min(v_corner_limit[i], 100.0)

        return v_corner_limit

    def solve_quasi_steady_velocity_profile(self, track: Track, deploy_strategy: np.ndarray = None, weather: WeatherConditions = None) -> np.ndarray:
        """
        Executes Forward-Backward Integration to generate the optimal velocity profile v(s):
        1. Apex cornering limit envelope
        2. Backward pass: Maximum adhesion braking into apexes
        3. Forward pass: Maximum traction acceleration out of apexes
        """
        w = weather if weather is not None else self.weather
        rho = w.air_density
        grip_factor = w.compute_track_grip_factor(getattr(self.p, "tire_compound", "SLICK"))
        mu_nom = self.p.mu_peak * 0.95 * grip_factor

        n_pts = len(track.s)
        ds = track.s[1] - track.s[0]

        # 1. Cornering limit
        v_limit = self.solve_cornering_speed_envelope(track, weather=w)

        # 2. Backward Braking Pass
        # We perform two cyclic sweeps to handle closed-loop periodic boundaries
        v_backward = np.copy(v_limit)
        for _ in range(2):
            for i in range(n_pts - 1, -1, -1):
                i_next = (i + 1) % n_pts
                v_next = v_backward[i_next]

                # Braking physics: F_brake = F_tire_x + F_drag + F_grade + F_rr
                q = 0.5 * rho * (v_next ** 2)
                f_down = q * self.p.cl_A_z_mode
                f_drag = q * self.p.cd_A_z_mode
                f_z = (self.p.total_mass * self.p.gravity) + f_down
                mu = mu_nom

                a_lat = (v_next ** 2) / track.corner_radius[i]
                f_y = self.p.total_mass * a_lat
                f_x_grip = np.sqrt(max(0.0, (mu * f_z) ** 2 - f_y ** 2))

                f_grade = self.p.total_mass * self.p.gravity * track.grade[i]
                f_rr = self.p.c_rr * self.p.total_mass * self.p.gravity

                # Max deceleration force
                f_decel = f_x_grip + f_drag + f_grade + f_rr
                a_decel = f_decel / self.p.total_mass

                # Kinematics v_i^2 = v_next^2 + 2 * a_decel * ds
                v_cand = np.sqrt(max(0.0, v_next ** 2 + 2 * a_decel * ds))
                if v_cand < v_backward[i]:
                    v_backward[i] = v_cand

        # 3. Forward Acceleration Pass
        v_forward = np.copy(v_backward)
        for _ in range(2):
            for i in range(n_pts):
                i_prev = (i - 1 + n_pts) % n_pts
                v_prev = v_forward[i_prev]

                # Determine aero mode
                curv = abs(track.curvature[i])
                aero_mode = AeroMode.Z_MODE if (curv > 0.002 or v_prev < 25.0) else AeroMode.X_MODE
                cl_a = self.p.cl_A_z_mode if aero_mode == AeroMode.Z_MODE else self.p.cl_A_x_mode
                cd_a = self.p.cd_A_z_mode if aero_mode == AeroMode.Z_MODE else self.p.cd_A_x_mode
                q = 0.5 * rho * (v_prev ** 2)
                f_down = q * cl_a
                f_drag = q * cd_a

                # Grip limit
                f_z = (self.p.total_mass * self.p.gravity) + f_down
                mu = mu_nom
                a_lat = (v_prev ** 2) / track.corner_radius[i]
                f_y = self.p.total_mass * a_lat
                f_x_grip = np.sqrt(max(0.0, (mu * f_z) ** 2 - f_y ** 2))

                # Powertrain tractive force
                deploy_factor = 1.0 if deploy_strategy is None else deploy_strategy[i]
                p_allowed_mguk = self.powertrain.get_mguk_tapered_cap(v_prev) * deploy_factor
                p_total = self.p.p_ice_max + p_allowed_mguk
                f_drive_raw = p_total / max(v_prev, 4.0)
                f_drive = min(f_drive_raw, f_x_grip)

                f_grade = self.p.total_mass * self.p.gravity * track.grade[i]
                f_rr = self.p.c_rr * self.p.total_mass * self.p.gravity

                f_accel = f_drive - f_drag - f_grade - f_rr
                a_accel = f_accel / self.p.total_mass

                # Kinematics v_i^2 = v_prev^2 + 2 * a_accel * ds
                v_cand = np.sqrt(max(10.0, v_prev ** 2 + 2 * a_accel * ds))
                if v_cand < v_forward[i]:
                    v_forward[i] = v_cand

        return v_forward

    def run_transient_simulation(self, track: Track, deploy_strategy: np.ndarray = None, initial_soc: float = None, weather: WeatherConditions = None) -> LapTelemetry:
        """
        Executes the high-precision Forward-Euler 0.01s Time-Stepping ODE Integration.
        Tracks state variables: s(t), v(t), SoC(t), T_tire(t).
        Incorporates real-world atmospheric air density, track surface grip factor, and wind vector.
        """
        w = weather if weather is not None else self.weather
        rho = w.air_density
        grip_factor = w.compute_track_grip_factor(getattr(self.p, "tire_compound", "SLICK"))

        dt = self.p.dt
        total_length = track.length

        # Generate target velocity reference from forward-backward solver
        v_target_profile = self.solve_quasi_steady_velocity_profile(track, deploy_strategy, weather=w)
        f_v_target = interp1d(track.s, v_target_profile, kind='linear', fill_value="extrapolate")

        # Interpolator for deployment strategy
        if deploy_strategy is None:
            deploy_strategy = np.ones_like(track.s)
        f_deploy = interp1d(track.s, deploy_strategy, kind='linear', fill_value="extrapolate")

        # Reset subsystem dynamic states
        self.powertrain.reset(initial_soc)
        self.tire.reset()

        # Initial state conditions
        s_current = 0.0
        v_current = float(v_target_profile[0])
        t_current = 0.0

        # Preallocate history buffers
        max_steps = int(250.0 / dt)  # Up to 250s max lap safety cap
        t_hist = np.zeros(max_steps)
        s_hist = np.zeros(max_steps)
        v_hist = np.zeros(max_steps)
        ax_hist = np.zeros(max_steps)
        ay_hist = np.zeros(max_steps)
        thr_hist = np.zeros(max_steps)
        brk_hist = np.zeros(max_steps)
        p_ice_hist = np.zeros(max_steps)
        p_mguk_hist = np.zeros(max_steps)
        soc_hist = np.zeros(max_steps)
        t_tire_hist = np.zeros(max_steps)
        mu_hist = np.zeros(max_steps)
        f_down_hist = np.zeros(max_steps)
        f_drag_hist = np.zeros(max_steps)
        gear_hist = np.zeros(max_steps, dtype=int)
        rpm_hist = np.zeros(max_steps)
        steer_hist = np.zeros(max_steps)
        fz_fl_hist = np.zeros(max_steps)
        fz_fr_hist = np.zeros(max_steps)
        fz_rl_hist = np.zeros(max_steps)
        fz_rr_hist = np.zeros(max_steps)
        bbw_hist = np.zeros(max_steps)
        aero_mode_hist = []

        step = 0
        soc_start = self.powertrain.soc_joules

        while s_current < total_length and step < max_steps:
            # 1. Track geometry at current arc length s
            s_query = min(s_current, total_length - 0.1)
            t_info = track.interpolate(s_query)
            radius = t_info["corner_radius"]
            grade_sin = t_info["grade"]
            grade_rad = np.arcsin(np.clip(grade_sin, -0.25, 0.25))
            heading_rad = t_info.get("heading", 0.0)

            # 2. Driver Control Demand with Lookahead Anticipation
            lookahead_dist = max(10.0, v_current * 0.22)
            s_look = min(s_current + lookahead_dist, total_length - 0.1)
            v_ref_here = float(f_v_target(s_query))
            v_ref_ahead = float(f_v_target(s_look))
            v_ref = min(v_ref_here, v_ref_ahead)

            speed_error = v_ref - v_current

            if speed_error > 0.2:
                # Accelerate
                throttle = float(np.clip(speed_error / 2.0, 0.25, 1.0))
                brake = 0.0
            elif speed_error < -0.2:
                # Threshold Deceleration / Braking
                throttle = 0.0
                brake = float(np.clip(-speed_error / 1.0, 0.40, 1.0))
            else:
                # Speed maintenance
                throttle = float(np.clip(0.3 + speed_error * 0.5, 0.0, 0.6))
                brake = 0.0

            # 3. Lateral Cornering Kinematics
            a_lat_demand = (v_current ** 2) / radius

            # 4. Active Aerodynamics with Wind Vector and Air Density
            aero_mode = self.aero.determine_mode(v_current, a_lat_demand, t_info["is_corner"], brake)
            v_aero = w.compute_relative_air_velocity(v_current, heading_rad)
            q_aero = 0.5 * rho * (v_aero ** 2)
            cl_a = self.p.cl_A_z_mode if aero_mode == AeroMode.Z_MODE else self.p.cl_A_x_mode
            cd_a = self.p.cd_A_z_mode if aero_mode == AeroMode.Z_MODE else self.p.cd_A_x_mode
            f_downforce = q_aero * cl_a
            f_drag = q_aero * cd_a

            # 5. Tire Mechanics with Track Temperature & Moisture Grip Factor
            f_z = (self.p.total_mass * self.p.gravity * np.cos(grade_rad)) + f_downforce
            f_z = max(1000.0, f_z)
            mu_base = self.tire.compute_mu(f_z, self.tire.t_tire)
            mu_eff = mu_base * grip_factor
            f_grip_max = mu_eff * f_z

            f_y_demand_unbounded = self.p.total_mass * abs(a_lat_demand)
            f_y_actual = min(f_y_demand_unbounded, f_grip_max)
            f_x_max_avail = np.sqrt(max(0.0, f_grip_max ** 2 - f_y_actual ** 2))
            a_lat_actual = f_y_actual / self.p.total_mass

            # 6. Powertrain Forces & Energy
            u_deploy = float(f_deploy(s_query))

            if throttle > 0.0:
                pt_state = self.powertrain.compute_drive_forces(
                    v_ms=v_current,
                    throttle=throttle,
                    deploy_factor=u_deploy,
                    f_x_grip_limit=f_x_max_avail
                )
                f_drive = pt_state.f_drive
                f_retard = 0.0
                p_deploy = pt_state.p_mguk_deploy
                p_regen = 0.0
            else:
                brake_demand = brake * self.p.f_brake_max_mechanical
                pt_state = self.powertrain.compute_braking_forces(
                    v_ms=v_current,
                    brake_demand_n=brake_demand,
                    f_x_grip_limit=f_x_max_avail
                )
                f_drive = 0.0
                f_retard = pt_state.f_brake_total
                p_deploy = 0.0
                p_regen = pt_state.p_mguk_regen

            # Resistive Forces: Aerodynamic Drag, Rolling Resistance, Grade
            f_rr = self.p.c_rr * self.p.total_mass * self.p.gravity * np.cos(grade_rad)
            f_grade = self.p.total_mass * self.p.gravity * grade_sin

            # 7. Longitudinal Physics ODE:
            # dv/dt = (F_drive - F_drag - F_rr - F_grade - F_retard) / M_total
            f_net = f_drive - f_retard - f_drag - f_rr - f_grade
            a_long = f_net / self.p.total_mass
            a_long_g = a_long / self.p.gravity
            a_lat_g = a_lat_actual / self.p.gravity

            # Dual-Track 4-Corner Dynamic Load Transfer & Steering Angle
            loads = self.dual_track.compute_4wheel_loads(
                a_long_g=a_long_g,
                a_lat_g=a_lat_g,
                f_downforce_total=f_downforce,
                grade_rad=grade_rad
            )
            grip_env = self.dual_track.evaluate_4wheel_grip_envelope(
                loads=loads,
                v_ms=v_current,
                radius_m=radius,
                t_tire_c=self.tire.t_tire,
                weather_grip_factor=grip_factor
            )

            # 8-Speed Sequential Transmission & Engine RPM Calculation
            p_drive_watts = (pt_state.p_ice + p_deploy) if throttle > 0.0 else 0.0
            tx_state = self.transmission.calculate_state(
                v_ms=v_current,
                throttle=throttle,
                p_total_watts=p_drive_watts,
                dt=dt
            )
            bbw_front = self.dual_track.compute_bbw_bias(a_long_g)

            # 8. Record Telemetry
            t_hist[step] = t_current
            s_hist[step] = s_current
            v_hist[step] = v_current
            ax_hist[step] = a_long_g                      # in g's
            ay_hist[step] = a_lat_g                       # in g's
            thr_hist[step] = throttle
            brk_hist[step] = brake
            p_ice_hist[step] = pt_state.p_ice / 1e3
            p_mguk_hist[step] = (p_deploy - p_regen) / 1e3  # Positive deploy, negative harvest (kW)
            soc_hist[step] = (self.powertrain.soc_joules / self.p.battery_capacity_joules) * 100.0
            t_tire_hist[step] = self.tire.t_tire
            mu_hist[step] = mu_eff
            f_down_hist[step] = f_downforce
            f_drag_hist[step] = f_drag
            gear_hist[step] = tx_state.gear
            rpm_hist[step] = tx_state.engine_rpm
            steer_hist[step] = grip_env.steer_angle_deg
            fz_fl_hist[step] = loads.f_z_fl
            fz_fr_hist[step] = loads.f_z_fr
            fz_rl_hist[step] = loads.f_z_rl
            fz_rr_hist[step] = loads.f_z_rr
            bbw_hist[step] = bbw_front * 100.0
            aero_mode_hist.append(aero_mode.name)

            # 9. Numerical Integration (Forward-Euler Steps)
            # Step vehicle motion
            v_next = max(0.5, v_current + a_long * dt)
            s_next = s_current + (v_current + v_next) * 0.5 * dt

            # Step powertrain SoC ODE
            self.powertrain.step_soc_ode(p_deploy, p_regen, dt)

            # Step tire thermal ODE with real ambient air temperature
            f_x_applied = f_drive if throttle > 0.0 else f_retard
            f_total = np.hypot(f_x_applied, f_y_actual)
            q_slip = self.p.k_heat_gen_slip * (f_total * (v_current + 5.0) * 0.08)
            q_carcass = 0.25 * (self.p.c_rr * f_z * v_current)
            q_gen = q_slip + q_carcass
            h_cool = self.p.h_cool_base + self.p.h_cool_speed_gain * v_current
            q_cool = h_cool * (self.tire.t_tire - w.air_temp_c)
            dt_tire = ((q_gen - q_cool) / self.p.c_tire_thermal) * dt
            self.tire.t_tire = max(w.air_temp_c, self.tire.t_tire + dt_tire)

            # Advance state
            v_current = v_next
            s_current = s_next
            t_current += dt
            step += 1

        # Slice buffers to completed steps
        delta_soc = ((self.powertrain.soc_joules - soc_start) / self.p.battery_capacity_joules) * 100.0

        return LapTelemetry(
            lap_time=t_current,
            distance_total=s_current,
            time=t_hist[:step],
            s=s_hist[:step],
            v=v_hist[:step],
            v_kmh=v_hist[:step] * 3.6,
            a_x=ax_hist[:step],
            a_y=ay_hist[:step],
            throttle=thr_hist[:step],
            brake=brk_hist[:step],
            p_ice_kw=p_ice_hist[:step],
            p_mguk_kw=p_mguk_hist[:step],
            soc_percent=soc_hist[:step],
            t_tire_c=t_tire_hist[:step],
            mu_eff=mu_hist[:step],
            f_downforce_n=f_down_hist[:step],
            f_drag_n=f_drag_hist[:step],
            aero_mode=np.array(aero_mode_hist),
            net_energy_deployed_mj=self.powertrain.lap_energy_deployed_joules / 1e6,
            net_energy_harvested_mj=self.powertrain.lap_energy_harvested_joules / 1e6,
            delta_soc_percent=delta_soc,
            gear=gear_hist[:step],
            engine_rpm=rpm_hist[:step],
            steering_angle_deg=steer_hist[:step],
            f_z_fl=fz_fl_hist[:step],
            f_z_fr=fz_fr_hist[:step],
            f_z_rl=fz_rl_hist[:step],
            f_z_rr=fz_rr_hist[:step],
            bbw_front_pct=bbw_hist[:step]
        )
