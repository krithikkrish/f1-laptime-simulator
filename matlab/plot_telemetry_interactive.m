function fig_handles = plot_telemetry_interactive(sim_results, track, ref_telemetry)
% PLOT_TELEMETRY_INTERACTIVE - Interactive MATLAB Multi-Channel Engineering Telemetry
%
% Renders:
% 1. Multi-Channel Telemetry (Speed, Inputs, Power, Battery SoC, Tires) with linked zoom/pan
% 2. 2D Circuit Map colored by speed with corner radius callouts
% 3. G-G Acceleration Diagram with 1g-5g friction circle limits

    if nargin < 2 || isempty(track)
        track.name = 'F1 Circuit';
        track.length = sim_results.distance_total;
    end
    if nargin < 3
        ref_telemetry = [];
    end

    s = sim_results.s;
    fig_handles = [];

    %% Figure 1: Multi-Channel Telemetry Dashboard
    f1 = figure('Name', ['F1 2026 Telemetry - ' track.name], 'Color', [0.07 0.09 0.11], ...
                'Position', [100, 100, 1200, 800]);
    fig_handles = [fig_handles, f1];

    % Subplot 1: Speed Profile
    ax(1) = subplot(5, 1, 1);
    plot(s, sim_results.v_kmh, 'Color', [0 1 0.53], 'LineWidth', 1.8, 'DisplayName', '2026 Simulation');
    hold on;
    if ~isempty(ref_telemetry) && isfield(ref_telemetry, 'speed') && isfield(ref_telemetry, 'distance_m')
        plot(ref_telemetry.distance_m, ref_telemetry.speed, 'Color', [0 0.9 1], 'LineWidth', 1.4, ...
             'LineStyle', ':', 'DisplayName', 'Real Pole Lap');
    end
    yline(290, '--', '2026 MGU-K Taper (290 km/h)', 'Color', [1 0.65 0], 'FontSize', 8);
    yline(345, '--', '2026 MGU-K Cutoff (345 km/h)', 'Color', [1 0.2 0.2], 'FontSize', 8);
    ylabel('Speed (km/h)', 'Color', [0.9 0.9 0.9], 'FontWeight', 'bold');
    grid on; set(gca, 'Color', [0.1 0.12 0.15], 'XColor', [0.5 0.5 0.5], 'YColor', [0.5 0.5 0.5]);
    title(sprintf('2026 F1 Lap-Time Simulation: %s | Lap Time: %.3f s | Top Speed: %.1f km/h', ...
                  track.name, sim_results.lap_time, sim_results.top_speed_kmh), ...
          'Color', [0 0.9 1], 'FontSize', 12);
    legend('Location', 'southeast', 'TextColor', [0.9 0.9 0.9]);

    % Subplot 2: Throttle & Brake
    ax(2) = subplot(5, 1, 2);
    plot(s, sim_results.throttle * 100, 'Color', [0 1 0.53], 'LineWidth', 1.4, 'DisplayName', 'Throttle %');
    hold on;
    area(s, sim_results.brake * 100, 'FaceColor', [1 0.1 0.25], 'FaceAlpha', 0.35, 'EdgeColor', [1 0.1 0.25], 'DisplayName', 'Brake %');
    ylabel('Inputs (%)', 'Color', [0.9 0.9 0.9], 'FontWeight', 'bold');
    ylim([-5, 105]);
    grid on; set(gca, 'Color', [0.1 0.12 0.15], 'XColor', [0.5 0.5 0.5], 'YColor', [0.5 0.5 0.5]);
    legend('Location', 'east', 'TextColor', [0.9 0.9 0.9]);

    % Subplot 3: Powertrain Deployment
    ax(3) = subplot(5, 1, 3);
    plot(s, sim_results.p_ice_kw, 'Color', [1 0.9 0.2], 'LineWidth', 1.4, 'DisplayName', 'ICE (kW)');
    hold on;
    area(s, sim_results.p_mguk_kw, 'FaceColor', [1 0.57 0], 'FaceAlpha', 0.35, 'EdgeColor', [1 0.57 0], 'DisplayName', 'MGU-K (kW)');
    ylabel('Power (kW)', 'Color', [0.9 0.9 0.9], 'FontWeight', 'bold');
    grid on; set(gca, 'Color', [0.1 0.12 0.15], 'XColor', [0.5 0.5 0.5], 'YColor', [0.5 0.5 0.5]);
    legend('Location', 'east', 'TextColor', [0.9 0.9 0.9]);

    % Subplot 4: Battery SoC
    ax(4) = subplot(5, 1, 4);
    area(s, sim_results.soc_percent, 'FaceColor', [0.83 0 0.97], 'FaceAlpha', 0.25, 'EdgeColor', [0.83 0 0.97], 'DisplayName', 'Battery SoC %');
    ylabel('SoC (%)', 'Color', [0.9 0.9 0.9], 'FontWeight', 'bold');
    grid on; set(gca, 'Color', [0.1 0.12 0.15], 'XColor', [0.5 0.5 0.5], 'YColor', [0.5 0.5 0.5]);
    legend('Location', 'east', 'TextColor', [0.9 0.9 0.9]);

    % Subplot 5: Tire Temperature
    ax(5) = subplot(5, 1, 5);
    plot(s, sim_results.t_tire_c, 'Color', [1 0.2 0.3], 'LineWidth', 1.6, 'DisplayName', 'Tire Temp (°C)');
    yline(100, ':', 'Optimum 100°C', 'Color', [0 1 0.5], 'FontSize', 8);
    xlabel('Track Distance (m)', 'Color', [0.9 0.9 0.9], 'FontWeight', 'bold');
    ylabel('Temp (°C)', 'Color', [0.9 0.9 0.9], 'FontWeight', 'bold');
    grid on; set(gca, 'Color', [0.1 0.12 0.15], 'XColor', [0.5 0.5 0.5], 'YColor', [0.5 0.5 0.5]);
    legend('Location', 'east', 'TextColor', [0.9 0.9 0.9]);

    % Synchronize horizontal zoom and pan across all 5 telemetry channels
    linkaxes(ax, 'x');
    xlim(ax(1), [0, sim_results.distance_total]);

    %% Figure 2: G-G Diagram & 2D Track Map
    f2 = figure('Name', ['F1 2026 Vehicle Dynamics - ' track.name], 'Color', [0.07 0.09 0.11], ...
                'Position', [150, 150, 1100, 520]);
    fig_handles = [fig_handles, f2];

    % Left: G-G Acceleration Diagram
    subplot(1, 2, 1);
    scatter(sim_results.a_y, sim_results.a_x, 8, sim_results.v_kmh, 'filled');
    hold on;
    theta = linspace(0, 2*pi, 100);
    for g = 1:5
        plot(g * cos(theta), g * sin(theta), ':', 'Color', [0.3 0.35 0.4]);
        text(0, g, sprintf('%dg', g), 'Color', [0.6 0.6 0.6], 'FontSize', 8);
    end
    xlabel('Lateral Acceleration a_y (g)', 'Color', [0.9 0.9 0.9]);
    ylabel('Longitudinal Acceleration a_x (g)', 'Color', [0.9 0.9 0.9]);
    title('G-G Friction Circle Diagram', 'Color', [0 0.9 1], 'FontSize', 11);
    axis equal; grid on;
    xlim([-5.5, 5.5]); ylim([-5.5, 3.5]);
    colormap(gca, turbo);
    c = colorbar; c.Color = [0.9 0.9 0.9]; ylabel(c, 'Speed (km/h)');
    set(gca, 'Color', [0.1 0.12 0.15], 'XColor', [0.5 0.5 0.5], 'YColor', [0.5 0.5 0.5]);

    % Right: 2D Track Map Colored by Speed
    subplot(1, 2, 2);
    if isfield(track, 'x') && isfield(track, 'y')
        v_interp = interp1(sim_results.s, sim_results.v_kmh, track.s, 'linear', 'extrap');
        scatter(track.x, track.y, 10, v_interp, 'filled');
        hold on;
        plot(track.x(1), track.y(1), 'p', 'MarkerSize', 14, 'MarkerFaceColor', [0 1 0.53], 'MarkerEdgeColor', 'w');
        text(track.x(1), track.y(1), '  Start/Finish', 'Color', [0 1 0.53], 'FontWeight', 'bold');
        title(['Circuit Speed Heatmap — ' track.name], 'Color', [0 1 0.53], 'FontSize', 11);
        axis equal; axis off;
        colormap(gca, turbo);
        c2 = colorbar; c2.Color = [0.9 0.9 0.9]; ylabel(c2, 'Speed (km/h)');
        set(gca, 'Color', [0.07 0.09 0.11]);
    end
end
