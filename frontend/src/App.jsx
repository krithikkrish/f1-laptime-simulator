import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import {
  Gauge,
  Zap,
  Battery,
  Flag,
  Flame,
  Activity,
  Play,
  Pause,
  HelpCircle,
  CheckCircle2,
  Sliders,
  Wind,
  Layers,
  ChevronRight,
  RotateCcw,
  Compass,
  Award
} from 'lucide-react';
import './index.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Ember Studio Chart styling options
const createEmberChartOptions = (yTitle, yMin = undefined, yMax = undefined) => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 250 },
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: { display: false }, // Dedicated separate HTML legend for each graph
    tooltip: {
      backgroundColor: '#1C1917',
      titleColor: '#FAFAF9',
      bodyColor: '#D6D3D1',
      borderColor: '#78716C',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      bodyFont: { family: 'Source Sans 3', size: 13 },
      titleFont: { family: 'Fira Code', size: 13, weight: 'bold' }
    }
  },
  scales: {
    x: {
      grid: { color: '#E7E5E4' },
      ticks: {
        color: '#78716C',
        font: { family: 'Fira Code', size: 11 },
        maxTicksLimit: 10,
        callback: (val) => `${Math.round(val)}m`
      },
      title: {
        display: true,
        text: 'Circuit Distance (Meters)',
        color: '#78716C',
        font: { family: 'Source Sans 3', size: 12, weight: '600' }
      }
    },
    y: {
      min: yMin,
      max: yMax,
      grid: { color: '#E7E5E4' },
      ticks: {
        color: '#57534E',
        font: { family: 'Fira Code', size: 11 }
      },
      title: {
        display: true,
        text: yTitle,
        color: '#1C1917',
        font: { family: 'Source Sans 3', size: 12, weight: '600' }
      }
    }
  }
});

export default function App() {
  const [tracks, setTracks] = useState([]);
  const [selectedTrackKey, setSelectedTrackKey] = useState('miami');
  const [compound, setCompound] = useState('Soft Slick');
  const [fuelKg, setFuelKg] = useState(25.0);
  const [setupMode, setSetupMode] = useState('balanced');
  const [activeTab, setActiveTab] = useState('telemetry');

  const [loading, setLoading] = useState(true);
  const [simData, setSimData] = useState(null);
  const [error, setError] = useState(null);

  // Live driving scrub state
  const [scrubDist, setScrubDist] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // 1. Fetch 2025 Calendar Tracks
  useEffect(() => {
    fetch('/api/tracks')
      .then(res => res.json())
      .then(data => {
        if (data.tracks && data.tracks.length > 0) {
          setTracks(data.tracks);
          if (!data.tracks.some(t => t.key === selectedTrackKey)) {
            setSelectedTrackKey(data.tracks[0].key);
          }
        }
      })
      .catch(err => {
        console.error('Error fetching tracks:', err);
        setError('Unable to connect to simulation server.');
      });
  }, []);

  // 2. Fetch Transient ODE Simulation against 2025 Benchmark
  useEffect(() => {
    if (!selectedTrackKey) return;
    setLoading(true);
    setError(null);

    fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        track_key: selectedTrackKey,
        compound: compound,
        fuel_kg: fuelKg,
        setup: setupMode
      })
    })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (data.error) throw new Error(data.error);
        setSimData(data);
        setScrubDist(0);
        setLoading(false);
      })
      .catch(err => {
        console.error('Simulation error:', err);
        setError(err.message || 'Simulation error');
        setLoading(false);
      });
  }, [selectedTrackKey, compound, fuelKg, setupMode]);

  // 3. Drive / Animate car along circuit
  useEffect(() => {
    if (!isPlaying || !simData?.track?.length_m) return;
    const trackLen = simData.track.length_m;
    const interval = setInterval(() => {
      setScrubDist(prev => (prev + 30) % trackLen);
    }, 40);
    return () => clearInterval(interval);
  }, [isPlaying, simData]);

  const telem = simData?.telemetry;
  const trackLen = simData?.track?.length_m || 5000;

  // Closest telemetry index for current car scrub position
  const currentIdx = useMemo(() => {
    if (!telem?.distance || telem.distance.length === 0) return 0;
    const distArr = telem.distance;
    let closest = 0;
    let minD = Infinity;
    for (let i = 0; i < distArr.length; i++) {
      const d = Math.abs(distArr[i] - scrubDist);
      if (d < minD) {
        minD = d;
        closest = i;
      }
    }
    return closest;
  }, [telem, scrubDist]);

  // Live telemetry values at scrubber position
  const liveSpeedKmh = telem?.speed_2026?.[currentIdx] ?? 0;
  const liveSpeedMph = Math.round(liveSpeedKmh * 0.621371);
  const liveGear = telem?.gear?.[currentIdx] ?? 1;
  const liveThrottle = Math.round(telem?.throttle?.[currentIdx] ?? 0);
  const liveBrake = Math.round(telem?.brake?.[currentIdx] ?? 0);
  const liveMguKw = Math.round(telem?.p_mguk_kw?.[currentIdx] ?? 0);
  const isAeroXMode = liveSpeedKmh > 260 && liveThrottle > 90;

  // Track map SVG geometry
  const mapSvgData = useMemo(() => {
    if (!simData?.track_map || simData.track_map.length === 0) return null;
    const pts = simData.track_map;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    pts.forEach(p => {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.y > maxY) maxY = p.y;
    });

    const pad = 40;
    const width = (maxX - minX) || 100;
    const height = (maxY - minY) || 100;
    const pathStr = pts.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`, '') + ' Z';

    const ratio = scrubDist / trackLen;
    const ptIdx = Math.min(Math.floor(ratio * pts.length), pts.length - 1);
    const carPos = pts[ptIdx] || pts[0];

    return {
      viewBox: `${minX - pad} ${minY - pad} ${width + pad * 2} ${height + pad * 2}`,
      pathStr,
      carPos
    };
  }, [simData?.track_map, scrubDist, trackLen]);

  // ==========================================
  // CHART 1: SPEED (2026 Sim vs 2025 Pole)
  // ==========================================
  const speedChartData = useMemo(() => {
    if (!telem) return null;
    const datasets = [
      {
        label: '2026 Simulation Car (50/50 Hybrid)',
        data: telem.speed_2026,
        borderColor: '#C2410C', // Terracotta
        backgroundColor: 'rgba(194, 65, 12, 0.08)',
        borderWidth: 2.8,
        tension: 0.2,
        pointRadius: 0,
        fill: true,
      }
    ];

    const poleSpeed = telem.speed_2025;
    if (poleSpeed) {
      datasets.push({
        label: `2025 Pole Lap (${simData.pole_benchmark.driver_name})`,
        data: poleSpeed,
        borderColor: '#0284C7', // Slate Cyan
        borderWidth: 2,
        borderDash: [5, 4],
        tension: 0.2,
        pointRadius: 0,
        fill: false,
      });
    }

    return { labels: telem.distance, datasets };
  }, [telem, simData]);

  // ==========================================
  // CHART 2: DRIVER INPUTS (Pedals & Gears)
  // ==========================================
  const inputsChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: 'Gas / Throttle (%)',
          data: telem.throttle,
          borderColor: '#16A34A', // Success green
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Brake Pressure (%)',
          data: telem.brake,
          borderColor: '#DC2626', // Error red
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Sequential Gear (x12.5)',
          data: telem.gear.map(g => g * 12.5),
          borderColor: '#D97706', // Amber warning
          borderWidth: 1.8,
          borderDash: [3, 3],
          pointRadius: 0,
          fill: false,
        }
      ]
    };
  }, [telem]);

  // ==========================================
  // CHART 3: POWERTRAIN (ICE vs MGU-K)
  // ==========================================
  const powertrainChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: '1.6L V6 Petrol Engine (kW)',
          data: telem.p_ice_kw,
          borderColor: '#EA580C', // Burnt orange
          borderWidth: 2.2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: '350 kW Electric MGU-K Motor (kW)',
          data: telem.p_mguk_kw,
          borderColor: '#7C3AED', // Violet
          backgroundColor: 'rgba(124, 58, 237, 0.08)',
          borderWidth: 2.2,
          pointRadius: 0,
          fill: true,
        }
      ]
    };
  }, [telem]);

  // ==========================================
  // CHART 4: BATTERY & TIRE TEMPERATURE
  // ==========================================
  const energyTireChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: 'Battery Charge Level (%)',
          data: telem.soc_pct,
          borderColor: '#0D9488', // Teal
          borderWidth: 2.2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Tire Surface Temp (°C)',
          data: telem.tire_temp,
          borderColor: '#E11D48', // Rose
          borderWidth: 2.2,
          pointRadius: 0,
          fill: false,
        }
      ]
    };
  }, [telem]);

  // ==========================================
  // CHART 5: DYNAMIC AXLE LOADS (kg)
  // ==========================================
  const loadChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: 'Front Axle Dynamic Load (kg)',
          data: telem.front_load_kg,
          borderColor: '#0284C7',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Rear Axle Dynamic Load (kg)',
          data: telem.rear_load_kg,
          borderColor: '#DB2777',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Aerodynamic Downforce (kg)',
          data: telem.downforce_kg,
          borderColor: '#CA8A04',
          borderWidth: 2,
          borderDash: [4, 4],
          pointRadius: 0,
          fill: false,
        }
      ]
    };
  }, [telem]);

  const activeTrackMeta = tracks.find(t => t.key === selectedTrackKey);

  return (
    <div className="ember-layout">
      {/* 1. Ember Studio Sidebar Navigation (256px) */}
      <aside className="ember-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand-title">
            <span>🏎️</span> Ember Studio
          </div>
          <div className="sidebar-brand-subtitle">
            Formula 1 Vehicle Dynamics Lab
          </div>
        </div>

        <div className="sidebar-content">
          <div className="sidebar-section-title">CHAMPIONSHIP CIRCUITS</div>
          {tracks.map(t => (
            <div
              key={t.key}
              className={`sidebar-nav-item ${selectedTrackKey === t.key ? 'active' : ''}`}
              onClick={() => setSelectedTrackKey(t.key)}
            >
              <span>{t.flag} {t.short_name}</span>
              <span style={{ fontSize: 11, fontFamily: 'var(--font-code)', color: 'var(--neutral)' }}>
                {Math.round(t.length_m / 1000 * 10) / 10} km
              </span>
            </div>
          ))}

          <div className="sidebar-section-title" style={{ marginTop: 16 }}>SYSTEM STATUS</div>
          <div style={{ padding: '8px 12px', fontSize: 13, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
            <CheckCircle2 size={15} /> 100 Hz ODE Engine Live
          </div>
          <div style={{ padding: '0 12px', fontSize: 12, color: 'var(--neutral)' }}>
            2025 FIA Ground-Effect Database
          </div>
        </div>
      </aside>

      {/* 2. Main Workstation Area */}
      <main className="ember-main">
        {/* Top App Bar */}
        <header className="ember-topbar">
          <div className="topbar-breadcrumbs">
            <span>Ember Studio</span>
            <span>/</span>
            <span>Championship Telemetry</span>
            <span>/</span>
            <strong>{activeTrackMeta?.country} GP ({activeTrackMeta?.short_name})</strong>
          </div>

          <div className="topbar-badge">
            <Award size={14} /> 2025 Benchmark Standard
          </div>
        </header>

        {/* Content Container (max-width 1200px) */}
        <div className="ember-container">
          {/* Header Title */}
          <div className="page-header">
            <h1 className="display-title">
              {activeTrackMeta?.flag} {simData?.track?.name || 'Grand Prix Circuit'}
            </h1>
            <p className="section-desc" style={{ marginTop: 6 }}>
              Comparative lap-time and transient energy deployment analysis of the 2026 Technical Regulations against the authentic 2025 qualifying standard.
            </p>
          </div>

          {/* 2025 Benchmark Banner */}
          {simData?.pole_benchmark && (
            <section className="benchmark-card">
              <div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, backgroundColor: '#FEE8DE', color: 'var(--primary)', padding: '3px 10px', borderRadius: 9999, fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                  <span>🏁</span> Official 2025 Saturday Q3 Qualifying Reference
                </div>
                <div style={{ fontSize: 15, color: 'var(--text-secondary)' }}>
                  Pole Sitter: <strong style={{ color: 'var(--text-primary)' }}>{simData.pole_benchmark.driver_name}</strong> ({simData.pole_benchmark.team_name})
                </div>
                <div style={{ fontSize: 13, color: 'var(--neutral)', marginTop: 2 }}>
                  Track Length: {Math.round(trackLen).toLocaleString()} meters | Real GPS Cartesian Waypoints
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 12, textTransform: 'uppercase', color: 'var(--neutral)', fontWeight: 600, letterSpacing: '0.05em' }}>
                  2025 Pole Lap Time
                </div>
                <div style={{ fontFamily: 'var(--font-code)', fontSize: 26, fontWeight: 700, color: 'var(--text-primary)' }}>
                  {simData.pole_benchmark.lap_time_str}
                </div>
              </div>
            </section>
          )}

          {/* User-Friendly One-Click Controls (Chips & Selects) */}
          <section className="controls-panel">
            <div>
              <label className="control-label">🛞 Pirelli Tire Compound</label>
              <div className="chip-group">
                {[
                  { id: 'Soft Slick', label: '🔴 Soft', hint: 'Maximum cornering adhesion' },
                  { id: 'Medium Slick', label: '🟡 Medium', hint: 'Balanced race compound' },
                  { id: 'Hard Slick', label: '⚪ Hard', hint: 'Durable low-wear compound' },
                  { id: 'Wet Weather', label: '🔵 Wet', hint: 'Heavy rain tread' },
                ].map(c => (
                  <button
                    key={c.id}
                    className={`ember-chip ${compound === c.id ? 'active' : ''}`}
                    onClick={() => setCompound(c.id)}
                    title={c.hint}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="control-label">⛽ Fuel Load on Board</label>
              <div className="chip-group">
                {[
                  { kg: 25.0, label: '⚡ Quali (25 kg)' },
                  { kg: 50.0, label: '⏱️ Sprint (50 kg)' },
                  { kg: 100.0, label: '🏁 Grand Prix (100 kg)' },
                ].map(f => (
                  <button
                    key={f.kg}
                    className={`ember-chip ${fuelKg === f.kg ? 'active' : ''}`}
                    onClick={() => setFuelKg(f.kg)}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="control-label">⚖️ Aerodynamic Setup Trim</label>
              <div className="chip-group">
                {[
                  { id: 'balanced', label: '⚖️ Balanced Spec' },
                  { id: 'high_speed', label: '🚀 Monza Low-Drag' },
                  { id: 'high_downforce', label: '🎯 Monaco High-Grip' },
                ].map(s => (
                  <button
                    key={s.id}
                    className={`ember-chip ${setupMode === s.id ? 'active' : ''}`}
                    onClick={() => setSetupMode(s.id)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Hero Verdict Banner */}
          {simData?.results && (
            <section className="verdict-hero-card">
              <div>
                <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--neutral)', fontWeight: 600 }}>
                  Simulated 2026 Lap Time
                </div>
                <div className="laptime-display">{simData.results.lap_time_str}</div>

                {simData.results.delta_s !== null && (
                  <div className={`delta-tag ${simData.results.faster_than_pole ? 'faster' : 'slower'}`}>
                    {simData.results.faster_than_pole
                      ? `🚀 ${Math.abs(simData.results.delta_s).toFixed(3)}s FASTER than 2025 Pole`
                      : `⏱️ +${simData.results.delta_s.toFixed(3)}s vs 2025 Pole Lap`}
                  </div>
                )}
              </div>

              <div style={{ maxWidth: 540, fontSize: 15, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                <p>
                  <strong>Race Engineering Assessment:</strong> {simData.results.faster_than_pole
                    ? `The 2026 specification car surpasses ${simData.pole_benchmark.driver_name}'s 2025 pole lap by ${Math.abs(simData.results.delta_s).toFixed(3)} seconds. Active aerodynamics (low-drag X-Mode on straights) combined with instant +470 hp electrical torque delivers superior exit speeds.`
                    : `The 2026 car is +${simData.results.delta_s.toFixed(3)} seconds off the 2025 pole mark. Reducing fuel load or switching to Soft Slicks will close the deficit through medium-speed corners.`}
                </p>
              </div>
            </section>
          )}

          {/* Four Key Metrics Cards */}
          {simData?.results && (
            <section className="metrics-grid">
              <div className="metric-card">
                <div className="metric-title" style={{ color: 'var(--primary)' }}>
                  <Activity size={14} /> 2026 LAP TIME
                </div>
                <div className="metric-value" style={{ color: 'var(--primary)' }}>
                  {simData.results.lap_time_str}
                </div>
                <div className="metric-desc">
                  2025 Real Pole: <strong>{simData.pole_benchmark.lap_time_str}</strong> ({simData.pole_benchmark.driver_name})
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-title" style={{ color: '#0284C7' }}>
                  <Gauge size={14} /> TOP SPEED
                </div>
                <div className="metric-value">
                  {Math.round(simData.results.top_speed_kmh)} <span style={{ fontSize: 16 }}>km/h</span>
                </div>
                <div className="metric-desc">
                  <strong>{Math.round(simData.results.top_speed_mph)} mph</strong> reached in X-Mode. 2025 Pole: <strong>{simData.pole_benchmark.top_speed_kmh} km/h</strong>
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-title" style={{ color: 'var(--accent)' }}>
                  <Zap size={14} /> ELECTRIC BOOST
                </div>
                <div className="metric-value" style={{ color: 'var(--accent)' }}>
                  350 kW <span style={{ fontSize: 16 }}>(+470 HP)</span>
                </div>
                <div className="metric-desc">
                  50% electrical power split delivers full torque out of turn apexes.
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-title" style={{ color: 'var(--success)' }}>
                  <Battery size={14} /> BATTERY FINISH
                </div>
                <div className="metric-value">
                  {Math.round(simData.results.battery_finish_soc)}% <span style={{ fontSize: 16 }}>SoC</span>
                </div>
                <div className="metric-desc">
                  Harvested <strong>{simData.results.energy_regen_mj.toFixed(2)} MJ</strong> under deceleration zones.
                </div>
              </div>
            </section>
          )}

          {/* Interactive Circuit Map & Live Cockpit */}
          <section className="visualizer-grid">
            {/* Left: Scaled Circuit Map */}
            <div className="ember-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <h3 className="section-title" style={{ fontSize: 18 }}>
                    {simData?.track?.flag} {simData?.track?.name}
                  </h3>
                  <div style={{ fontSize: 12, color: 'var(--neutral)' }}>
                    Length: {Math.round(trackLen).toLocaleString()} meters | Real GPS Spline Geometry
                  </div>
                </div>

                <button
                  className="ember-btn-primary"
                  style={{ padding: '6px 14px', fontSize: 13 }}
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                  {isPlaying ? 'Pause Lap' : 'Drive Lap'}
                </button>
              </div>

              <div className="track-canvas-box">
                {mapSvgData && (
                  <svg className="track-svg" viewBox={mapSvgData.viewBox}>
                    <path
                      d={mapSvgData.pathStr}
                      fill="none"
                      stroke="#D6D3D1"
                      strokeWidth="24"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d={mapSvgData.pathStr}
                      fill="none"
                      stroke="#FAFAF9"
                      strokeWidth="16"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d={mapSvgData.pathStr}
                      fill="none"
                      stroke="#C2410C"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    {mapSvgData.carPos && (
                      <g transform={`translate(${mapSvgData.carPos.x}, ${mapSvgData.carPos.y})`}>
                        <circle r="18" fill="rgba(194, 65, 12, 0.2)" />
                        <circle r="10" fill="#C2410C" stroke="#FFFFFF" strokeWidth="2.5" />
                      </g>
                    )}
                  </svg>
                )}
              </div>

              {/* Scrubber slider */}
              <div className="scrub-container">
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--neutral)', marginBottom: 4 }}>
                  <span>0 m</span>
                  <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Position: {Math.round(scrubDist)} m</span>
                  <span>{Math.round(trackLen)} m</span>
                </div>
                <input
                  type="range"
                  className="scrub-range"
                  min="0"
                  max={trackLen}
                  step="10"
                  value={scrubDist}
                  onChange={e => {
                    setScrubDist(parseFloat(e.target.value));
                    if (isPlaying) setIsPlaying(false);
                  }}
                />
              </div>
            </div>

            {/* Right: Live Cockpit Telemetry Display */}
            <div className="ember-card">
              <div style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--neutral)', marginBottom: 12 }}>
                🏎️ Live Cockpit Telemetry
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
                <div style={{ backgroundColor: '#E7E5E4', padding: 14, borderRadius: 8 }}>
                  <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--neutral)', fontWeight: 600 }}>Live Speed</div>
                  <div style={{ fontFamily: 'var(--font-code)', fontSize: 26, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {Math.round(liveSpeedKmh)} <span style={{ fontSize: 14 }}>km/h</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{liveSpeedMph} mph</div>
                </div>

                <div style={{ backgroundColor: '#E7E5E4', padding: 14, borderRadius: 8 }}>
                  <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--neutral)', fontWeight: 600 }}>Transmission</div>
                  <div style={{ fontFamily: 'var(--font-code)', fontSize: 26, fontWeight: 700, color: 'var(--primary)' }}>
                    Gear {liveGear}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>8-Speed Seamless</div>
                </div>
              </div>

              {/* Pedals */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-secondary)' }}>
                  <span>Gas / Throttle Pedal</span>
                  <strong style={{ color: 'var(--success)' }}>{liveThrottle}%</strong>
                </div>
                <div className="ember-progress-track">
                  <div className="ember-progress-fill" style={{ width: `${liveThrottle}%`, backgroundColor: 'var(--success)' }}></div>
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--text-secondary)' }}>
                  <span>Brake Pedal</span>
                  <strong style={{ color: 'var(--error)' }}>{liveBrake}%</strong>
                </div>
                <div className="ember-progress-track">
                  <div className="ember-progress-fill" style={{ width: `${liveBrake}%`, backgroundColor: 'var(--error)' }}></div>
                </div>
              </div>

              <div style={{ backgroundColor: '#E7E5E4', padding: 14, borderRadius: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                  <span style={{ color: 'var(--neutral)' }}>⚡ MGU-K Motor:</span>
                  <strong style={{ color: liveMguKw >= 0 ? 'var(--primary)' : 'var(--success)' }}>
                    {liveMguKw >= 0 ? `+${liveMguKw} kW (Deploying)` : `${liveMguKw} kW (Regenerating)`}
                  </strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                  <span style={{ color: 'var(--neutral)' }}>💨 Active Wings:</span>
                  <strong style={{ color: isAeroXMode ? 'var(--primary)' : 'var(--text-primary)' }}>
                    {isAeroXMode ? 'Active Aero Open (Low Drag X-Mode)' : 'Cornering Wing (High Downforce Z-Mode)'}
                  </strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ color: 'var(--neutral)' }}>🛞 Fitted Tires:</span>
                  <strong style={{ color: 'var(--text-primary)' }}>{compound}</strong>
                </div>
              </div>
            </div>
          </section>

          {/* 5 Modular Decongested Telemetry Charts (Separate Legends, 2025 Data Only) */}
          <section style={{ marginTop: 24 }}>
            <div style={{ marginBottom: 20 }}>
              <h2 className="section-title">Telemetry & Dynamic Performance</h2>
              <p className="section-desc">
                Dedicated independent engineering channels comparing 2026 vehicle dynamics directly against the 2025 championship standard.
              </p>
            </div>

            {/* CHART 1: Speed Profile */}
            <div className="chart-card">
              <div className="chart-header">
                <div className="chart-heading-group">
                  <h3 className="chart-title">
                    <Gauge size={18} color="var(--primary)" /> 1. Speed Profile & Lap Comparison
                  </h3>
                  <span className="chart-subtitle">
                    Overlay of 2026 simulation speed vs {simData?.pole_benchmark?.driver_name}'s authentic 2025 qualifying pole lap.
                  </span>
                </div>

                <div className="chart-legend-row">
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#C2410C' }}></span>
                    <span>2026 Simulation Car</span>
                  </div>
                  {simData?.pole_benchmark && (
                    <div className="legend-badge">
                      <span className="legend-pill-color" style={{ backgroundColor: '#0284C7' }}></span>
                      <span>2025 Pole: {simData.pole_benchmark.driver_name} ({simData.pole_benchmark.lap_time_str})</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="chart-viewport">
                {speedChartData && <Line data={speedChartData} options={createEmberChartOptions('Speed (km/h)', 0, 370)} />}
              </div>
            </div>

            {/* CHART 2: Driver Pedals & Gears */}
            <div className="chart-card">
              <div className="chart-header">
                <div className="chart-heading-group">
                  <h3 className="chart-title">
                    <Activity size={18} color="var(--success)" /> 2. Driver Inputs & Sequential Transmission
                  </h3>
                  <span className="chart-subtitle">
                    Gas pedal percentage, hydraulic brake line pressure, and 8-speed gear changes.
                  </span>
                </div>

                <div className="chart-legend-row">
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#16A34A' }}></span>
                    <span>Gas / Throttle (%)</span>
                  </div>
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#DC2626' }}></span>
                    <span>Brake (%)</span>
                  </div>
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#D97706' }}></span>
                    <span>Gear Selection (1-8)</span>
                  </div>
                </div>
              </div>

              <div className="chart-viewport">
                {inputsChartData && <Line data={inputsChartData} options={createEmberChartOptions('Inputs (%)', 0, 105)} />}
              </div>
            </div>

            {/* CHART 3: Powertrain Curves */}
            <div className="chart-card">
              <div className="chart-header">
                <div className="chart-heading-group">
                  <h3 className="chart-title">
                    <Zap size={18} color="var(--primary)" /> 3. Hybrid Powertrain Energy Distribution
                  </h3>
                  <span className="chart-subtitle">
                    1.6L V6 Turbo combustion engine (400 kW) vs 350 kW Electric MGU-K motor deployment & harvesting.
                  </span>
                </div>

                <div className="chart-legend-row">
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#EA580C' }}></span>
                    <span>1.6L V6 Petrol Engine (kW)</span>
                  </div>
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#7C3AED' }}></span>
                    <span>Electric MGU-K Motor (kW)</span>
                  </div>
                </div>
              </div>

              <div className="chart-viewport">
                {powertrainChartData && <Line data={powertrainChartData} options={createEmberChartOptions('Power (kW)', -360, 420)} />}
              </div>
            </div>

            {/* CHART 4: Energy & Tire Thermals */}
            <div className="chart-card">
              <div className="chart-header">
                <div className="chart-heading-group">
                  <h3 className="chart-title">
                    <Battery size={18} color="#0D9488" /> 4. Battery State of Charge & Tire Surface Thermals
                  </h3>
                  <span className="chart-subtitle">
                    Energy recovery through braking zones and bulk tire tread temperature (°C).
                  </span>
                </div>

                <div className="chart-legend-row">
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#0D9488' }}></span>
                    <span>Battery SoC (%)</span>
                  </div>
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#E11D48' }}></span>
                    <span>Tire Temperature (°C)</span>
                  </div>
                </div>
              </div>

              <div className="chart-viewport">
                {energyTireChartData && <Line data={energyTireChartData} options={createEmberChartOptions('Level (% / °C)', 0, 130)} />}
              </div>
            </div>

            {/* CHART 5: Dynamic Axle Loads (kg) */}
            <div className="chart-card">
              <div className="chart-header">
                <div className="chart-heading-group">
                  <h3 className="chart-title">
                    <Wind size={18} color="#0284C7" /> 5. Dynamic Axle Vertical Loads & Aerodynamic Downforce
                  </h3>
                  <span className="chart-subtitle">
                    Physical forces measured in kilograms (kg) across corner entry, apex, and straightaway compression.
                  </span>
                </div>

                <div className="chart-legend-row">
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#0284C7' }}></span>
                    <span>Front Axle Load (kg)</span>
                  </div>
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#DB2777' }}></span>
                    <span>Rear Axle Load (kg)</span>
                  </div>
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#CA8A04' }}></span>
                    <span>Aerodynamic Downforce (kg)</span>
                  </div>
                </div>
              </div>

              <div className="chart-viewport">
                {loadChartData && <Line data={loadChartData} options={createEmberChartOptions('Vertical Load (kg)', 0, undefined)} />}
              </div>
            </div>
          </section>

          {/* Educational Guide in Ember Studio Craft Aesthetic */}
          <section className="ember-card" style={{ marginTop: 24, padding: 28 }}>
            <h3 className="section-title" style={{ fontSize: 22, marginBottom: 12 }}>
              Understanding the 2026 Technical Regulations
            </h3>
            <p className="section-desc" style={{ marginBottom: 20 }}>
              The 2026 FIA technical regulations represent the largest powertrain and aerodynamic overhaul in modern motorsport history.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
              <div style={{ backgroundColor: '#E7E5E4', padding: 16, borderRadius: 8 }}>
                <strong style={{ color: 'var(--primary)', display: 'block', fontSize: 15, marginBottom: 4 }}>
                  ⚡ 50/50 Powertrain Equality
                </strong>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  The 2026 regulations triple the electric contribution to 350 kW (470 hp), paired with an efficient 400 kW (536 hp) turbocharged combustion unit on 100% sustainable fuel.
                </p>
              </div>

              <div style={{ backgroundColor: '#E7E5E4', padding: 16, borderRadius: 8 }}>
                <strong style={{ color: '#0284C7', display: 'block', fontSize: 15, marginBottom: 4 }}>
                  💨 Active Wing Aerodynamics
                </strong>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Replacing traditional DRS, automated front and rear wings switch synchronously between high-downforce "Z-Mode" in cornering phases and low-drag "X-Mode" on straights.
                </p>
              </div>

              <div style={{ backgroundColor: '#E7E5E4', padding: 16, borderRadius: 8 }}>
                <strong style={{ color: 'var(--warning)', display: 'block', fontSize: 15, marginBottom: 4 }}>
                  📉 Electrical Speed Tapering
                </strong>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  To manage energy over an entire lap, maximum electric deployment occurs between 0 and 290 km/h, automatically tapering down as top speed is sustained by the combustion engine.
                </p>
              </div>

              <div style={{ backgroundColor: '#E7E5E4', padding: 16, borderRadius: 8 }}>
                <strong style={{ color: 'var(--success)', display: 'block', fontSize: 15, marginBottom: 4 }}>
                  🔋 High-Capacity Harvesting
                </strong>
                <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Under heavy braking into chicanes and hairpins, the MGU-K generates up to 350 kW of electrical regeneration, capturing critical energy without conventional brake wear.
                </p>
              </div>
            </div>
          </section>

          {/* Footer */}
          <footer className="ember-footer">
            Ember Studio • Formula 1 2026 Transient Lap-Time Simulator & 2025 Championship Benchmark Database.
          </footer>
        </div>
      </main>
    </div>
  );
}
