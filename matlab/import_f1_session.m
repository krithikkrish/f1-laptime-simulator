function [track, weather, ref_telemetry] = import_f1_session(mat_filepath)
% IMPORT_F1_SESSION - Imports real-world circuit geometry, weather, and reference telemetry
%
% Usage:
%   [track, weather, ref_telemetry] = import_f1_session('monza_session.mat');

    if nargin < 1 || isempty(mat_filepath)
        error('Please specify a valid path to a .mat session file.');
    end

    if ~isfile(mat_filepath)
        error('File not found: %s', mat_filepath);
    end

    data = load(mat_filepath);

    if isfield(data, 'track')
        track = data.track;
    else
        % Construct track struct from raw fields
        track.name = data.circuit_name;
        track.s = data.track_s;
        track.x = data.track_x;
        track.y = data.track_y;
        track.z = data.track_z;
        track.curvature = data.track_curvature;
        track.corner_radius = data.track_corner_radius;
        track.grade = data.track_grade;
        track.heading = data.track_heading;
        track.length = data.track_length;
    end

    if isfield(data, 'weather')
        weather = data.weather;
    else
        weather.air_temp_c = data.air_temp_c;
        weather.track_temp_c = data.track_temp_c;
        weather.humidity_pct = data.humidity_pct;
        weather.pressure_hpa = data.pressure_hpa;
        weather.wind_speed_ms = data.wind_speed_ms;
        weather.wind_dir_deg = data.wind_dir_deg;
        weather.rainfall = data.rainfall;
    end

    if isfield(data, 'ref_telemetry')
        ref_telemetry = data.ref_telemetry;
    else
        ref_telemetry = [];
    end

    fprintf('[MATLAB] Successfully loaded session for %s\n', track.name);
    fprintf('         Track Length: %.1f m | Air Temp: %.1f°C | Track Temp: %.1f°C\n', ...
            track.length, weather.air_temp_c, weather.track_temp_c);
end
