% RUN_MATLAB_BATCH - Batch test and execution script for 2026 F1 LTS Simulator in MATLAB
%
% Runs a 0.01s Forward-Euler simulation on Autodromo Nazionale Monza, prints
% race engineering KPIs, and renders the interactive telemetry suite.

clear; clc; close all;
fprintf('=================================================================\n');
fprintf('  2026 F1 TRANSIENT LAP-TIME SIMULATOR (MATLAB ENGINE)          \n');
fprintf('  Forward-Euler 0.01s ODE Integrator | 350kW MGU-K | Active Aero \n');
fprintf('=================================================================\n\n');

% 1. Load Session Data
mat_file = fullfile(fileparts(mfilename('fullpath')), 'monza_session.mat');
if ~isfile(mat_file)
    error('Session file not found: %s. Run Python exporter first.', mat_file);
end

[track, weather, ref_telemetry] = import_f1_session(mat_file);

% 2. Vehicle & Regulatory Parameters (2026 Technical Regulations)
params.mass_empty = 768.0;          % Minimum mass (kg)
params.mass_driver = 80.0;          % Driver + ballast (kg)
params.fuel_mass = 40.0;            % Qualifying fuel load (kg)
params.gravity = 9.80665;
params.c_rr = 0.015;

% Active Aerodynamics
params.cl_A_z = 3.20;               % Z-Mode (Cornering High Downforce)
params.cd_A_z = 1.15;
params.cl_A_x = 1.10;               % X-Mode (Straight Low Drag)
params.cd_A_x = 0.65;

% 2026 Powertrain: 400kW ICE + 350kW MGU-K
params.p_ice_max = 400e3;
params.p_mguk_max = 350e3;
params.v_taper_start = 290 / 3.6;   % 290 km/h
params.v_taper_end = 345 / 3.6;     % 345 km/h

% Energy Storage & Brakes
params.es_capacity = 8.5e6;         % 8.5 MJ
params.soc_initial = 0.65;          % 65% SoC
params.f_brake_max = 65000;

% Tire Dynamics
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
params.dt = 0.01;                   % 0.01s time step

% 3. Run Numerical Simulation
fprintf('[MATLAB] Running 0.01s Forward-Euler Integration loop...\n');
tic;
sim_results = f1_lts_simulation(track, weather, params);
sim_time = toc;

% 4. Report Engineering KPIs
fprintf('\n----------------- SIMULATION RESULTS -----------------\n');
fprintf('  Circuit:                   %s\n', track.name);
fprintf('  Lap Time:                  %.3f s (1m %05.2fs)\n', ...
        sim_results.lap_time, mod(sim_results.lap_time, 60));
fprintf('  Top Speed:                 %.1f km/h (%.1f m/s)\n', ...
        sim_results.top_speed_kmh, sim_results.top_speed_kmh / 3.6);
fprintf('  MGU-K Energy Deployed:     %.2f MJ (FIA Limit: 4.0 MJ/lap)\n', ...
        sim_results.net_energy_deployed_mj);
fprintf('  MGU-K Energy Harvested:    %.2f MJ\n', ...
        sim_results.net_energy_harvested_mj);
fprintf('  Final Battery SoC:         %.2f%% (Start: %.2f%%)\n', ...
        sim_results.soc_percent(end), params.soc_initial * 100);
fprintf('  Peak Tire Temperature:     %.1f °C\n', ...
        max(sim_results.t_tire_c));
fprintf('  Integration Compute Time:  %.3f s (%d time-steps)\n', ...
        sim_time, length(sim_results.time));
fprintf('------------------------------------------------------\n\n');

% 5. Save Output
save(fullfile(fileparts(mfilename('fullpath')), 'sim_results_monza.mat'), 'sim_results', 'track');
fprintf('[MATLAB] Saved simulation results to sim_results_monza.mat\n');

% 6. Plot Interactive Telemetry (if running with display)
if usejava('desktop') || usejava('awt')
    plot_telemetry_interactive(sim_results, track, ref_telemetry);
end
