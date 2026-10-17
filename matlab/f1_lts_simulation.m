function [sim_results] = f1_lts_simulation(track, weather, params)
% F1_LTS_SIMULATION - 2026 Formula 1 Transient Lap-Time Simulation Engine
% 
% High-precision Forward-Euler 0.01s time-stepping numerical integrator:
% - Longitudinal Newton mechanics: dv/dt = (F_drive - F_drag - F_rr - F_grade - F_brake) / M
% - 2026 FIA MGU-K Hybrid: 350kW electric deploy with 290-345 km/h tapering curve
% - Active Aerodynamics: Z-Mode (Cornering downforce) vs X-Mode (Straight low-drag)
% - Thermal Tire Model: dT/dt = (Q_gen - Q_cool) / C_thermal
% - Environmental Physics: CIPM-2007 humid air density rho(p, T, rh) & track grip mu(T_track)
%
% Inputs:
%   track   - Struct with fields: s, x, y, z, curvature, corner_radius, grade, heading, length
%   weather - (Optional) Struct with fields: air_temp_c, track_temp_c, humidity_pct, pressure_hpa, wind_speed_ms, wind_dir_deg, rainfall
%   params  - (Optional) Struct with vehicle & powertrain regulatory parameters
%
% Output:
%   sim_results - Struct containing time-series arrays for all telemetry channels

    %% 1. Default Parameters Setup
    if nargin < 2 || isempty(weather)
        weather.air_temp_c = 25.0;
        weather.track_temp_c = 38.0;
        weather.humidity_pct = 50.0;
        weather.pressure_hpa = 1013.25;
        weather.wind_speed_ms = 2.0;
        weather.wind_dir_deg = 90.0;
        weather.rainfall = 0;
    end

    if nargin < 3 || isempty(params)
        params.mass_empty = 768.0;      % 2026 minimum car mass (kg)
        params.mass_driver = 80.0;      % Driver + seat standard (kg)
        params.fuel_mass = 40.0;        % Qualifying fuel load (kg)
        params.gravity = 9.80665;
        params.c_rr = 0.015;            % Rolling resistance coefficient
        
        % 2026 Active Aero Specifications
        params.cl_A_z = 3.20;           % Z-Mode downforce area (m^2)
        params.cd_A_z = 1.15;           % Z-Mode drag area (m^2)
        params.cl_A_x = 1.10;           % X-Mode downforce area (m^2)
        params.cd_A_x = 0.65;           % X-Mode drag area (m^2)
        
        % Powertrain Specifications
        params.p_ice_max = 400e3;       % 400 kW 1.6L V6 Turbo
        params.p_mguk_max = 350e3;      % 350 kW 2026 MGU-K deploy / regen
        params.v_taper_start = 290 / 3.6; % 290 km/h (m/s)
        params.v_taper_end = 345 / 3.6;   % 345 km/h (m/s)
        
        % Battery / Energy Storage
        params.es_capacity = 8.5e6;     % 8.5 MJ total capacity
        params.soc_initial = 0.65;      % 65% initial SoC
        params.f_brake_max = 65000;     % Mechanical braking capacity (N)
        
        % Tire Model
        params.mu_peak = 1.72;
        params.fz_ref = 4000.0;
        params.load_sens = 0.000030;
        params.t_tire_opt = 100.0;
        params.t_tire_sigma = 25.0;
        params.t_tire_initial = 90.0;
        params.c_thermal = 1800.0;
        params.h_cool_base = 20.0;
        params.h_cool_speed = 0.65;
        params.k_heat_slip = 0.045;
        
        params.dt = 0.01;               % 0.01s time step
    end

    total_mass = params.mass_empty + params.mass_driver + params.fuel_mass;

    %% 2. CIPM-2007 Humid Air Density & Track Surface Grip Calculation
    p_pa = weather.pressure_hpa * 100.0;
    T_k = weather.air_temp_c + 273.15;
    p_sat = 610.78 * exp((17.27 * weather.air_temp_c) / (weather.air_temp_c + 237.3));
    p_v = (weather.humidity_pct / 100.0) * p_sat;
    p_d = max(1000.0, p_pa - p_v);
    rho = (p_d / (287.058 * T_k)) + (p_v / (461.495 * T_k));
    rho = min(max(rho, 0.80), 1.45);

    % Asphalt temperature grip scaling factor
    T_track = weather.track_temp_c;
    if weather.rainfall > 0
        grip_factor = 0.65;
    elseif T_track >= 32.0 && T_track <= 44.0
        grip_factor = 1.0;
    elseif T_track < 32.0
        delta = 32.0 - T_track;
        grip_factor = 1.0 - 0.0035 * delta - 0.00015 * (delta^2);
    else
        delta = T_track - 44.0;
        grip_factor = 1.0 - 0.0025 * delta - 0.00010 * (delta^2);
    end
    grip_factor = min(max(grip_factor, 0.75), 1.05);
    mu_nom = params.mu_peak * 0.95 * grip_factor;

    %% 3. Forward-Backward Speed Envelope Solver
    n_pts = length(track.s);
    ds = track.s(2) - track.s(1);
    v_corner_limit = zeros(1, n_pts);

    for i = 1:n_pts
        R = track.corner_radius(i);
        theta = asin(min(max(track.grade(i), -0.2), 0.2));
        g_eff = params.gravity * cos(theta);
        denom = (1.0 / R) - (0.5 * rho * params.cl_A_z * mu_nom / total_mass);
        if denom <= 0
            v_corner_limit(i) = 100.0;
        else
            v_corner_limit(i) = min(sqrt((mu_nom * g_eff) / denom), 100.0);
        end
    end

    % Backward Braking Pass
    v_backward = v_corner_limit;
    for sweep = 1:2
        for i = n_pts:-1:1
            i_next = mod(i, n_pts) + 1;
            v_nxt = v_backward(i_next);
            q = 0.5 * rho * (v_nxt^2);
            f_down = q * params.cl_A_z;
            f_drag = q * params.cd_A_z;
            f_z = (total_mass * params.gravity) + f_down;
            a_lat = (v_nxt^2) / track.corner_radius(i);
            f_y = total_mass * a_lat;
            f_x_grip = sqrt(max(0.0, (mu_nom * f_z)^2 - f_y^2));
            f_grade = total_mass * params.gravity * track.grade(i);
            f_rr = params.c_rr * total_mass * params.gravity;
            f_decel = f_x_grip + f_drag + f_grade + f_rr;
            a_decel = f_decel / total_mass;
            v_cand = sqrt(max(0.0, v_nxt^2 + 2 * a_decel * ds));
            if v_cand < v_backward(i)
                v_backward(i) = v_cand;
            end
        end
    end

    % Forward Acceleration Pass
    v_forward = v_backward;
    for sweep = 1:2
        for i = 1:n_pts
            i_prev = mod(i - 2 + n_pts, n_pts) + 1;
            v_prv = v_forward(i_prev);
            curv = abs(track.curvature(i));
            if curv > 0.002 || v_prv < 25.0
                cl_a = params.cl_A_z;
                cd_a = params.cd_A_z;
            else
                cl_a = params.cl_A_x;
                cd_a = params.cd_A_x;
            end
            q = 0.5 * rho * (v_prv^2);
            f_down = q * cl_a;
            f_drag = q * cd_a;
            f_z = (total_mass * params.gravity) + f_down;
            a_lat = (v_prv^2) / track.corner_radius(i);
            f_y = total_mass * a_lat;
            f_x_grip = sqrt(max(0.0, (mu_nom * f_z)^2 - f_y^2));
            
            % 2026 MGU-K Power Taper Curve
            if v_prv <= params.v_taper_start
                p_mguk_avail = params.p_mguk_max;
            elseif v_prv >= params.v_taper_end
                p_mguk_avail = 0.0;
            else
                frac = (params.v_taper_end - v_prv) / (params.v_taper_end - params.v_taper_start);
                p_mguk_avail = params.p_mguk_max * frac;
            end
            
            p_total = params.p_ice_max + p_mguk_avail;
            f_drive = min(p_total / max(v_prv, 4.0), f_x_grip);
            f_grade = total_mass * params.gravity * track.grade(i);
            f_rr = params.c_rr * total_mass * params.gravity;
            f_accel = f_drive - f_drag - f_grade - f_rr;
            a_accel = f_accel / total_mass;
            v_cand = sqrt(max(10.0, v_prv^2 + 2 * a_accel * ds));
            if v_cand < v_forward(i)
                v_forward(i) = v_cand;
            end
        end
    end

    %% 4. High-Precision Forward-Euler 0.01s Time-Stepping ODE Integration
    dt = params.dt;
    max_steps = round(250.0 / dt);
    
    t_hist = zeros(1, max_steps);
    s_hist = zeros(1, max_steps);
    v_hist = zeros(1, max_steps);
    ax_hist = zeros(1, max_steps);
    ay_hist = zeros(1, max_steps);
    thr_hist = zeros(1, max_steps);
    brk_hist = zeros(1, max_steps);
    p_ice_hist = zeros(1, max_steps);
    p_mguk_hist = zeros(1, max_steps);
    soc_hist = zeros(1, max_steps);
    t_tire_hist = zeros(1, max_steps);
    f_down_hist = zeros(1, max_steps);
    f_drag_hist = zeros(1, max_steps);

    s_curr = 0.0;
    v_curr = v_forward(1);
    t_curr = 0.0;
    soc_joules = params.es_capacity * params.soc_initial;
    t_tire = params.t_tire_initial;
    tot_deployed_j = 0.0;
    tot_harvested_j = 0.0;
    step = 1;

    while s_curr < track.length && step <= max_steps
        s_norm = mod(s_curr, track.length);
        idx = max(1, min(n_pts - 1, floor(s_norm / ds) + 1));
        radius = track.corner_radius(idx);
        grade_val = track.grade(idx);
        hdg = track.heading(idx);
        
        v_ref = v_forward(idx);
        speed_err = v_ref - v_curr;

        if speed_err > 0.2
            throttle = min(max(speed_err / 2.0, 0.25), 1.0);
            brake = 0.0;
        elseif speed_err < -0.2
            throttle = 0.0;
            brake = min(max(-speed_err / 1.0, 0.40), 1.0);
        else
            throttle = min(max(0.3 + speed_err * 0.5, 0.0), 0.6);
            brake = 0.0;
        end

        % Lateral demand
        a_lat_demand = (v_curr^2) / radius;

        % Active Aerodynamics with Wind Vector
        is_corner = abs(track.curvature(idx)) > 0.0025;
        if is_corner || abs(a_lat_demand) > 8.0 || brake > 0.15 || v_curr < 25.0
            cl_a = params.cl_A_z;
            cd_a = params.cd_A_z;
            is_z_mode = true;
        else
            cl_a = params.cl_A_x;
            cd_a = params.cd_A_x;
            is_z_mode = false;
        end

        % Relative airspeed
        wind_rad = deg2rad(weather.wind_dir_deg);
        v_aero = max(0.0, v_curr + weather.wind_speed_ms * cos(hdg - wind_rad));
        q_aero = 0.5 * rho * (v_aero^2);
        f_down = q_aero * cl_a;
        f_drag = q_aero * cd_a;

        % Tire Mechanics
        f_z = total_mass * params.gravity + f_down;
        delta_fz = max(0.0, f_z - params.fz_ref);
        mu_load = max(0.85, params.mu_peak * (1.0 - params.load_sens * delta_fz));
        t_diff = t_tire - params.t_tire_opt;
        thermal_fac = 0.70 + 0.30 * exp(-0.5 * (t_diff / params.t_tire_sigma)^2);
        mu_eff = mu_load * thermal_fac * grip_factor;
        f_grip_max = mu_eff * f_z;
        f_y_actual = min(total_mass * abs(a_lat_demand), f_grip_max);
        f_x_max_avail = sqrt(max(0.0, f_grip_max^2 - f_y_actual^2));
        a_lat_actual = f_y_actual / total_mass;

        % Powertrain Forces
        if throttle > 0.0
            if v_curr <= params.v_taper_start
                p_mguk_cap = params.p_mguk_max;
            elseif v_curr >= params.v_taper_end
                p_mguk_cap = 0.0;
            else
                p_mguk_cap = params.p_mguk_max * (params.v_taper_end - v_curr) / (params.v_taper_end - params.v_taper_start);
            end
            
            p_mguk_deploy = throttle * p_mguk_cap;
            p_ice = throttle * params.p_ice_max;
            f_drive_raw = (p_ice + p_mguk_deploy) / max(v_curr, 4.0);
            f_drive = min(f_drive_raw, f_x_max_avail);
            f_retard = 0.0;
            p_regen = 0.0;
        else
            f_drive = 0.0;
            p_ice = 0.0;
            p_mguk_deploy = 0.0;
            brake_demand = brake * params.f_brake_max;
            f_regen_raw = min(brake_demand, params.p_mguk_max / max(v_curr, 4.0));
            f_regen = min(f_regen_raw, f_x_max_avail);
            p_regen = f_regen * v_curr;
            f_retard = min(brake_demand, f_x_max_avail);
        end

        f_rr = params.c_rr * total_mass * params.gravity;
        f_grade = total_mass * params.gravity * grade_val;
        f_net = f_drive - f_retard - f_drag - f_rr - f_grade;
        a_long = f_net / total_mass;

        % Record Step
        t_hist(step) = t_curr;
        s_hist(step) = s_curr;
        v_hist(step) = v_curr;
        ax_hist(step) = a_long / params.gravity;
        ay_hist(step) = a_lat_actual / params.gravity;
        thr_hist(step) = throttle;
        brk_hist(step) = brake;
        p_ice_hist(step) = p_ice / 1e3;
        p_mguk_hist(step) = (p_mguk_deploy - p_regen) / 1e3;
        soc_hist(step) = (soc_joules / params.es_capacity) * 100.0;
        t_tire_hist(step) = t_tire;
        f_down_hist(step) = f_down;
        f_drag_hist(step) = f_drag;

        % ODE Integration
        v_next = max(0.5, v_curr + a_long * dt);
        s_next = s_curr + (v_curr + v_next) * 0.5 * dt;

        % SoC ODE
        soc_joules = soc_joules - (p_mguk_deploy / 0.94) * dt + (p_regen * 0.90) * dt;
        soc_joules = min(max(soc_joules, 0.05 * params.es_capacity), 0.98 * params.es_capacity);
        tot_deployed_j = tot_deployed_j + p_mguk_deploy * dt;
        tot_harvested_j = tot_harvested_j + p_regen * dt;

        % Tire Thermal ODE
        f_x_app = max(f_drive, f_retard);
        f_tot = hypot(f_x_app, f_y_actual);
        q_slip = params.k_heat_slip * (f_tot * (v_curr + 5.0) * 0.08);
        q_carcass = 0.25 * (params.c_rr * f_z * v_curr);
        h_cool = params.h_cool_base + params.h_cool_speed * v_curr;
        q_cool = h_cool * (t_tire - weather.air_temp_c);
        dt_tire = ((q_slip + q_carcass - q_cool) / params.c_thermal) * dt;
        t_tire = max(weather.air_temp_c, t_tire + dt_tire);

        v_curr = v_next;
        s_curr = s_next;
        t_curr = t_curr + dt;
        step = step + 1;
    end

    n_valid = step - 1;

    %% 5. Pack Structured Results
    sim_results.lap_time = t_curr;
    sim_results.distance_total = s_curr;
    sim_results.time = t_hist(1:n_valid);
    sim_results.s = s_hist(1:n_valid);
    sim_results.v = v_hist(1:n_valid);
    sim_results.v_kmh = v_hist(1:n_valid) * 3.6;
    sim_results.a_x = ax_hist(1:n_valid);
    sim_results.a_y = ay_hist(1:n_valid);
    sim_results.throttle = thr_hist(1:n_valid);
    sim_results.brake = brk_hist(1:n_valid);
    sim_results.p_ice_kw = p_ice_hist(1:n_valid);
    sim_results.p_mguk_kw = p_mguk_hist(1:n_valid);
    sim_results.soc_percent = soc_hist(1:n_valid);
    sim_results.t_tire_c = t_tire_hist(1:n_valid);
    sim_results.f_downforce_n = f_down_hist(1:n_valid);
    sim_results.f_drag_n = f_drag_hist(1:n_valid);
    sim_results.net_energy_deployed_mj = tot_deployed_j / 1e6;
    sim_results.net_energy_harvested_mj = tot_harvested_j / 1e6;
    sim_results.top_speed_kmh = max(sim_results.v_kmh);
    sim_results.weather = weather;
    sim_results.params = params;
end
