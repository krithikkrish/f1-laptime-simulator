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
  ChevronDown,
  Info
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

// Shared base options for clean, decongested Chart.js graphs
const createBaseChartOptions = (yTitle, yMin = undefined, yMax = undefined) => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 300 },
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    legend: { display: false }, // Using custom dedicated separate legend above each graph
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      titleColor: '#f3f4f6',
      bodyColor: '#e5e7eb',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderWidth: 1,
      padding: 10,
      bodyFont: { family: 'Inter', size: 12 },
      titleFont: { family: 'Outfit', size: 13, weight: 'bold' }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(255, 255, 255, 0.04)' },
      ticks: {
        color: '#6b7280',
        font: { family: 'JetBrains Mono', size: 11 },
        maxTicksLimit: 10,
        callback: (val, idx, ticks) => `${Math.round(val)}m`
      },
      title: {
        display: true,
        text: 'Track Distance (Meters)',
        color: '#6b7280',
        font: { family: 'Inter', size: 11 }
      }
    },
    y: {
      min: yMin,
      max: yMax,
      grid: { color: 'rgba(255, 255, 255, 0.05)' },
      ticks: {
        color: '#9ca3af',
        font: { family: 'JetBrains Mono', size: 11 }
      },
      title: {
        display: true,
        text: yTitle,
        color: '#9ca3af',
        font: { family: 'Inter', size: 11, weight: 'bold' }
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
  
  const [loading, setLoading] = useState(true);
  const [simData, setSimData] = useState(null);
  const [error, setError] = useState(null);

  // Live scrub & animation state
  const [scrubDist, setScrubDist] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const animRef = useRef(null);

  // 1. Fetch available tracks list on load
  useEffect(() => {
    fetch('/api/tracks')
      .then(res => res.json())
      .then(data => {
        if (data.tracks && data.tracks.length > 0) {
          setTracks(data.tracks);
          // Keep current selection or default to miami / first track
          if (!data.tracks.some(t => t.key === selectedTrackKey)) {
            setSelectedTrackKey(data.tracks[0].key);
          }
        }
      })
      .catch(err => {
        console.error('Error fetching tracks:', err);
        setError('Failed to load track calendar.');
      });
  }, []);

  // 2. Fetch transient simulation telemetry when parameters change
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

  // 3. Play / Animate car along track
  useEffect(() => {
    if (!isPlaying || !simData?.track?.length_m) return;

    const trackLen = simData.track.length_m;
    const interval = setInterval(() => {
      setScrubDist(prev => (prev + 35) % trackLen);
    }, 40);

    return () => clearInterval(interval);
  }, [isPlaying, simData]);

  // Telemetry arrays & current scrub index
  const telem = simData?.telemetry;
  const trackLen = simData?.track?.length_m || 5000;

  const currentIdx = useMemo(() => {
    if (!telem?.distance || telem.distance.length === 0) return 0;
    const distArr = telem.distance;
    let closestIdx = 0;
    let minDiff = Infinity;
    for (let i = 0; i < distArr.length; i++) {
      const diff = Math.abs(distArr[i] - scrubDist);
      if (diff < minDiff) {
        minDiff = diff;
        closestIdx = i;
      }
    }
    return closestIdx;
  }, [telem, scrubDist]);

  // Live cockpit values at scrubber location
  const liveSpeedKmh = telem?.speed_2026?.[currentIdx] ?? 0;
  const liveSpeedMph = Math.round(liveSpeedKmh * 0.621371);
  const liveGear = telem?.gear?.[currentIdx] ?? 1;
  const liveThrottle = Math.round(telem?.throttle?.[currentIdx] ?? 0);
  const liveBrake = Math.round(telem?.brake?.[currentIdx] ?? 0);
  const liveMguKw = Math.round(telem?.p_mguk_kw?.[currentIdx] ?? 0);
  const isAeroXMode = liveSpeedKmh > 260 && liveThrottle > 90;

  // Track map SVG geometry calculation
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

    // Interpolate current car position on map
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
  // CHART 1: SPEED PROFILE (2026 vs 2024 Pole)
  // ==========================================
  const speedChartData = useMemo(() => {
    if (!telem) return null;
    const datasets = [
      {
        label: '2026 Formula 1 Sim (Hybrid 50/50)',
        data: telem.speed_2026,
        borderColor: '#00ff88',
        backgroundColor: 'rgba(0, 255, 136, 0.08)',
        borderWidth: 2.8,
        tension: 0.25,
        pointRadius: 0,
        fill: true,
      }
    ];

    if (telem.speed_2024) {
      datasets.push({
        label: `2024 Real Pole Lap (${simData.pole_benchmark.driver_name})`,
        data: telem.speed_2024,
        borderColor: '#00e5ff',
        borderWidth: 2.2,
        borderDash: [5, 4],
        tension: 0.25,
        pointRadius: 0,
        fill: false,
      });
    }

    return {
      labels: telem.distance,
      datasets
    };
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
          label: 'Gas Pedal / Throttle (%)',
          data: telem.throttle,
          borderColor: '#10b981',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Brake Pedal (%)',
          data: telem.brake,
          borderColor: '#ef4444',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Sequential Gear (x10)',
          data: telem.gear.map(g => g * 12.5), // Scaled 1-8 to 0-100%
          borderColor: '#f59e0b',
          borderWidth: 1.8,
          borderDash: [3, 3],
          pointRadius: 0,
          fill: false,
        }
      ]
    };
  }, [telem]);

  // ==========================================
  // CHART 3: 2026 POWERTRAIN (ICE vs MGU-K)
  // ==========================================
  const powertrainChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: '1.6L V6 Petrol Engine (kW)',
          data: telem.p_ice_kw,
          borderColor: '#f97316',
          borderWidth: 2.2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Electric MGU-K Motor (kW)',
          data: telem.p_mguk_kw,
          borderColor: '#a855f7',
          backgroundColor: 'rgba(168, 85, 247, 0.08)',
          borderWidth: 2.2,
          pointRadius: 0,
          fill: true,
        }
      ]
    };
  }, [telem]);

  // ==========================================
  // CHART 4: BATTERY SOC & TIRE THERMALS
  // ==========================================
  const energyTireChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: 'Battery Charge Level (%)',
          data: telem.soc_pct,
          borderColor: '#14b8a6',
          borderWidth: 2.2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Tire Surface Temp (°C)',
          data: telem.tire_temp,
          borderColor: '#f43f5e',
          borderWidth: 2.2,
          pointRadius: 0,
          fill: false,
        }
      ]
    };
  }, [telem]);

  // ==========================================
  // CHART 5: AXLE VERTICAL LOADS (kg)
  // ==========================================
  const loadChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: 'Front Axle Dynamic Load (kg)',
          data: telem.front_load_kg,
          borderColor: '#38bdf8',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Rear Axle Dynamic Load (kg)',
          data: telem.rear_load_kg,
          borderColor: '#ec4899',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Aerodynamic Downforce (kg)',
          data: telem.downforce_kg,
          borderColor: '#eab308',
          borderWidth: 2,
          borderDash: [4, 4],
          pointRadius: 0,
          fill: false,
        }
      ]
    };
  }, [telem]);

  const selectedTrackMeta = tracks.find(t => t.key === selectedTrackKey);

  return (
    <div className="app-container">
      {/* 1. Header with F1 Branding & Status */}
      <header className="app-header">
        <div>
          <div className="brand-badge">
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00ff88', display: 'inline-block' }}></span>
            FIA F1 2026 Transient Lap-Time Simulator
          </div>
          <h1 className="brand-title">Pit-Wall Telemetry Workstation</h1>
          <p className="brand-subtitle">
            100 Hz Transient Vehicle Dynamics ODE Engine & Authentic 2024 Pole Benchmarks
          </p>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Engine Status</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#00ff88', display: 'flex', alignItems: 'center', gap: 6 }}>
              <CheckCircle2 size={16} /> REST API Online
            </div>
          </div>
        </div>
      </header>

      {/* 2. Top Circuit Selector & Clear 2024 Pole Benchmark Callout */}
      <section className="benchmark-banner">
        <div className="circuit-selector-wrap">
          <label className="selector-label" htmlFor="circuit-select">
            <Flag size={14} /> Grand Prix Circuit (24 World Championship Venues)
          </label>
          <select
            id="circuit-select"
            className="circuit-dropdown"
            value={selectedTrackKey}
            onChange={e => setSelectedTrackKey(e.target.value)}
          >
            {tracks.map(t => (
              <option key={t.key} value={t.key}>
                {t.flag} {t.country} — {t.short_name} ({Math.round(t.length_m).toLocaleString()} m)
              </option>
            ))}
          </select>
        </div>

        {simData?.pole_benchmark && (
          <div className="pole-benchmark-details">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span className="pole-tag">2024 BENCHMARK</span>
                <span style={{ fontSize: 12, color: '#9ca3af' }}>Official Saturday Qualifying (Q3)</span>
              </div>
              <div className="pole-meta-text">
                Pole Sitter: <span className="pole-meta-highlight">{simData.pole_benchmark.driver_name}</span> ({simData.pole_benchmark.team_name})
              </div>
            </div>
            <div style={{ textAlign: 'right', borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: 16 }}>
              <div style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase' }}>Pole Lap Time</div>
              <div className="pole-lap-display">{simData.pole_benchmark.lap_time_str}</div>
            </div>
          </div>
        )}
      </section>

      {/* 3. One-Click User-Friendly Driver Controls */}
      <section className="controls-card">
        <div>
          <div className="control-group-title">
            <span>🛞</span> Tire Compound (Pirelli F1)
          </div>
          <div className="pill-group">
            {[
              { id: 'Soft Slick', label: '🔴 Soft', desc: 'Fastest Qualifying Grip' },
              { id: 'Medium Slick', label: '🟡 Medium', desc: 'Balanced Race Compound' },
              { id: 'Hard Slick', label: '⚪ Hard', desc: 'Durable Low-Wear' },
              { id: 'Wet Weather', label: '🔵 Wet', desc: 'Heavy Rain Tread' },
            ].map(c => (
              <button
                key={c.id}
                className={`pill-btn ${compound === c.id ? 'active' : ''}`}
                onClick={() => setCompound(c.id)}
                title={c.desc}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="control-group-title">
            <span>⛽</span> Fuel Tank Load
          </div>
          <div className="pill-group">
            {[
              { kg: 25.0, label: '⚡ Quali (25 kg)', desc: 'Minimum weight for maximum speed' },
              { kg: 50.0, label: '⏱️ Sprint (50 kg)', desc: 'Half-tank sprint race balance' },
              { kg: 100.0, label: '🏁 Grand Prix (100 kg)', desc: 'Full starting race fuel load' },
            ].map(f => (
              <button
                key={f.kg}
                className={`pill-btn ${fuelKg === f.kg ? 'active' : ''}`}
                onClick={() => setFuelKg(f.kg)}
                title={f.desc}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="control-group-title">
            <Sliders size={14} /> Aerodynamic Setup Trim
          </div>
          <div className="pill-group">
            {[
              { id: 'balanced', label: '⚖️ Balanced Spec', desc: 'Standard high-downforce & active low-drag' },
              { id: 'high_speed', label: '🚀 Low-Drag Monza', desc: 'Ultra-low drag for 350+ km/h straights' },
              { id: 'high_downforce', label: '🎯 High-Downforce', desc: 'Maximum cornering adhesion for Monaco' },
            ].map(s => (
              <button
                key={s.id}
                className={`pill-btn ${setupMode === s.id ? 'active' : ''}`}
                onClick={() => setSetupMode(s.id)}
                title={s.desc}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 4. Hero Lap Verdict Banner */}
      {simData?.results && (
        <section className="hero-verdict-card">
          <div>
            <div style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: 'var(--text-muted)', fontWeight: 700 }}>
              Simulated 2026 Lap Time
            </div>
            <div className="hero-laptime">{simData.results.lap_time_str}</div>
            
            {simData.results.delta_s !== null && (
              <div className={`delta-badge ${simData.results.faster_than_pole ? 'faster' : 'slower'}`}>
                {simData.results.faster_than_pole
                  ? `🚀 ${Math.abs(simData.results.delta_s).toFixed(3)}s FASTER than 2024 Pole`
                  : `⏱️ +${simData.results.delta_s.toFixed(3)}s vs 2024 Pole Lap`}
              </div>
            )}
          </div>

          <div className="hero-verdict-text">
            <p>
              <strong>Race Engineer Summary:</strong> {simData.results.faster_than_pole
                ? `The 2026 specification car beats ${simData.pole_benchmark.driver_name}'s 2024 pole lap by ${Math.abs(simData.results.delta_s).toFixed(3)}s! The combination of Active Aerodynamics (low-drag X-Mode) and +470 hp electric boost delivers superior acceleration out of every turn.`
                : `The 2026 car is +${simData.results.delta_s.toFixed(3)}s off the 2024 benchmark. Try switching to Soft Slicks or reducing fuel to 25 kg to extract peak qualifying pace.`}
            </p>
          </div>
        </section>
      )}

      {/* 5. Four Big Clear Stat Cards */}
      {simData?.results && (
        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-label" style={{ color: '#00ff88' }}>
              <Activity size={14} /> 2026 LAP TIME
            </div>
            <div className="stat-val" style={{ color: '#00ff88' }}>{simData.results.lap_time_str}</div>
            <div className="stat-desc">
              2024 Real Pole: <strong style={{ color: '#fff' }}>{simData.pole_benchmark.lap_time_str}</strong> ({simData.pole_benchmark.driver_name})
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label" style={{ color: '#00e5ff' }}>
              <Gauge size={14} /> TOP SPEED
            </div>
            <div className="stat-val" style={{ color: '#00e5ff' }}>
              {Math.round(simData.results.top_speed_kmh)} <span style={{ fontSize: 16 }}>km/h</span>
            </div>
            <div className="stat-desc">
              <strong>{Math.round(simData.results.top_speed_mph)} mph</strong> in low-drag X-Mode. 2024 Pole: <strong style={{ color: '#fff' }}>{simData.pole_benchmark.top_speed_kmh} km/h</strong>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label" style={{ color: '#f97316' }}>
              <Zap size={14} /> ELECTRIC BOOST
            </div>
            <div className="stat-val" style={{ color: '#f97316' }}>
              350 kW <span style={{ fontSize: 16 }}>(+470 HP)</span>
            </div>
            <div className="stat-desc">
              50% electric hybrid ratio delivers instant torque out of corner apexes.
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label" style={{ color: '#a855f7' }}>
              <Battery size={14} /> BATTERY FINISH
            </div>
            <div className="stat-val" style={{ color: '#a855f7' }}>
              {Math.round(simData.results.battery_finish_soc)}% <span style={{ fontSize: 16 }}>SoC</span>
            </div>
            <div className="stat-desc">
              Harvested <strong>{simData.results.energy_regen_mj.toFixed(2)} MJ</strong> of kinetic energy under heavy braking zones.
            </div>
          </div>
        </section>
      )}

      {/* 6. Interactive Visualizer: Scaled Track Map + Live Cockpit Telemetry */}
      <section className="visualizer-section">
        {/* Left: 2D Track Map */}
        <div className="visualizer-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 800 }}>
                {simData?.track?.flag} {simData?.track?.name}
              </h3>
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Track Length: {Math.round(trackLen).toLocaleString()} meters | Real GPS Cartesian Waypoints
              </p>
            </div>

            <button
              className={`pill-btn ${isPlaying ? 'active' : ''}`}
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? <Pause size={14} /> : <Play size={14} />}
              {isPlaying ? 'Pause Car' : 'Drive Lap'}
            </button>
          </div>

          <div className="track-map-container">
            {mapSvgData && (
              <svg className="track-svg" viewBox={mapSvgData.viewBox}>
                {/* Circuit layout line */}
                <path
                  d={mapSvgData.pathStr}
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.2)"
                  strokeWidth="28"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d={mapSvgData.pathStr}
                  fill="none"
                  stroke="#1e293b"
                  strokeWidth="20"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d={mapSvgData.pathStr}
                  fill="none"
                  stroke="rgba(0, 229, 255, 0.4)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Animated / Scrubber Car dot */}
                {mapSvgData.carPos && (
                  <g transform={`translate(${mapSvgData.carPos.x}, ${mapSvgData.carPos.y})`}>
                    <circle r="22" fill="rgba(0, 255, 136, 0.25)" />
                    <circle r="14" fill="#00ff88" stroke="#ffffff" strokeWidth="3" />
                  </g>
                )}
              </svg>
            )}
          </div>

          {/* Scrubber slider to scrub around the circuit */}
          <div className="scrubber-wrap">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              <span>Start / Finish (0m)</span>
              <span style={{ color: '#00ff88', fontWeight: 700 }}>Car Position: {Math.round(scrubDist)}m</span>
              <span>Lap End ({Math.round(trackLen)}m)</span>
            </div>
            <input
              type="range"
              className="scrubber-slider"
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

        {/* Right: Live Cockpit Dashboard */}
        <div className="visualizer-card">
          <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)', fontWeight: 700, marginBottom: 8 }}>
            🏎️ Live Cockpit Telemetry
          </div>

          <div className="cockpit-gauge-grid">
            <div className="cockpit-metric">
              <div style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase' }}>Live Speed</div>
              <div className="cockpit-metric-val" style={{ color: '#00e5ff' }}>
                {Math.round(liveSpeedKmh)} <span style={{ fontSize: 14 }}>km/h</span>
              </div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{liveSpeedMph} mph</div>
            </div>

            <div className="cockpit-metric">
              <div style={{ fontSize: 11, color: '#9ca3af', textTransform: 'uppercase' }}>Current Gear</div>
              <div className="cockpit-metric-val" style={{ color: '#f59e0b' }}>
                {liveGear}
              </div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>8-Speed Seamless</div>
            </div>
          </div>

          {/* Throttle & Brake Bars */}
          <div className="bar-container">
            <div className="bar-header">
              <span>Throttle / Gas Pedal</span>
              <strong style={{ color: '#10b981' }}>{liveThrottle}%</strong>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${liveThrottle}%`, background: '#10b981' }}></div>
            </div>
          </div>

          <div className="bar-container">
            <div className="bar-header">
              <span>Brake Pedal</span>
              <strong style={{ color: '#ef4444' }}>{liveBrake}%</strong>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${liveBrake}%`, background: '#ef4444' }}></div>
            </div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', padding: 12, borderRadius: 10, marginTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
              <span style={{ color: '#9ca3af' }}>⚡ Electric MGU-K:</span>
              <strong style={{ color: liveMguKw >= 0 ? '#00ff88' : '#38bdf8' }}>
                {liveMguKw >= 0 ? `+${liveMguKw} kW (Deploying)` : `${liveMguKw} kW (Harvesting)`}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
              <span style={{ color: '#9ca3af' }}>💨 Active Wing Aero:</span>
              <strong style={{ color: isAeroXMode ? '#00e5ff' : '#f59e0b' }}>
                {isAeroXMode ? 'Active Aero Open (Low Drag X-Mode)' : 'Cornering Wing (High Downforce Z-Mode)'}
              </strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: '#9ca3af' }}>🛞 Tire Compound:</span>
              <strong style={{ color: '#fff' }}>{compound}</strong>
            </div>
          </div>
        </div>
      </section>

      {/* 7. MODULAR TELEMETRY CHARTS (DECONGESTED, SEPARATE LEGEND FOR EACH GRAPH, DISTINCT COLOURS) */}
      <section style={{ marginTop: 32 }}>
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 24, fontWeight: 900 }}>
            📊 Modular Telemetry Analysis
          </h2>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
            Each graph has its own dedicated legend, vibrant high-contrast colors, and independent axes.
          </p>
        </div>

        {/* GRAPH 1: Speed Comparison */}
        <div className="chart-card">
          <div className="chart-header">
            <div className="chart-title-wrap">
              <div className="chart-title" style={{ color: '#00ff88' }}>
                <Gauge size={20} /> 1. Speed Profile & Lap Comparison
              </div>
              <div className="chart-subtitle">
                Comparing 2026 simulation against {simData?.pole_benchmark?.driver_name}'s authentic 2024 qualifying pole lap.
              </div>
            </div>

            {/* SEPARATE DEDICATED LEGEND FOR GRAPH 1 */}
            <div className="chart-legend">
              <div className="legend-item" style={{ borderColor: '#00ff88' }}>
                <span className="legend-line" style={{ background: '#00ff88' }}></span>
                <span style={{ color: '#00ff88' }}>2026 F1 Sim (Hybrid 50/50)</span>
              </div>
              {simData?.pole_benchmark && (
                <div className="legend-item" style={{ borderColor: '#00e5ff' }}>
                  <span className="legend-line" style={{ background: '#00e5ff', borderTop: '2px dashed #00e5ff', height: 0 }}></span>
                  <span style={{ color: '#00e5ff' }}>2024 Pole: {simData.pole_benchmark.driver_name} ({simData.pole_benchmark.lap_time_str})</span>
                </div>
              )}
            </div>
          </div>

          <div className="chart-canvas-wrap">
            {speedChartData && <Line data={speedChartData} options={createBaseChartOptions('Speed (km/h)', 0, 370)} />}
          </div>
        </div>

        {/* GRAPH 2: Driver Pedals & Sequential Gears */}
        <div className="chart-card">
          <div className="chart-header">
            <div className="chart-title-wrap">
              <div className="chart-title" style={{ color: '#10b981' }}>
                <Activity size={20} /> 2. Driver Inputs & Sequential Transmission
              </div>
              <div className="chart-subtitle">
                Gas pedal percentage (0-100%), brake pedal pressure, and 8-speed gear changes.
              </div>
            </div>

            {/* SEPARATE DEDICATED LEGEND FOR GRAPH 2 */}
            <div className="chart-legend">
              <div className="legend-item" style={{ borderColor: '#10b981' }}>
                <span className="legend-dot" style={{ background: '#10b981' }}></span>
                <span style={{ color: '#10b981' }}>Gas Pedal (%)</span>
              </div>
              <div className="legend-item" style={{ borderColor: '#ef4444' }}>
                <span className="legend-dot" style={{ background: '#ef4444' }}></span>
                <span style={{ color: '#ef4444' }}>Brake Pedal (%)</span>
              </div>
              <div className="legend-item" style={{ borderColor: '#f59e0b' }}>
                <span className="legend-line" style={{ background: '#f59e0b' }}></span>
                <span style={{ color: '#f59e0b' }}>Gear Selection (1-8)</span>
              </div>
            </div>
          </div>

          <div className="chart-canvas-wrap">
            {inputsChartData && <Line data={inputsChartData} options={createBaseChartOptions('Pedal Inputs (%)', 0, 105)} />}
          </div>
        </div>

        {/* GRAPH 3: Powertrain Power Curves */}
        <div className="chart-card">
          <div className="chart-header">
            <div className="chart-title-wrap">
              <div className="chart-title" style={{ color: '#f97316' }}>
                <Zap size={20} /> 3. 2026 Hybrid Powertrain Output
              </div>
              <div className="chart-subtitle">
                1.6L V6 Turbo combustion engine (400 kW) vs 350 kW Electric MGU-K deployment and brake regeneration.
              </div>
            </div>

            {/* SEPARATE DEDICATED LEGEND FOR GRAPH 3 */}
            <div className="chart-legend">
              <div className="legend-item" style={{ borderColor: '#f97316' }}>
                <span className="legend-line" style={{ background: '#f97316' }}></span>
                <span style={{ color: '#f97316' }}>1.6L V6 Petrol Engine (kW)</span>
              </div>
              <div className="legend-item" style={{ borderColor: '#a855f7' }}>
                <span className="legend-dot" style={{ background: '#a855f7' }}></span>
                <span style={{ color: '#a855f7' }}>Electric MGU-K Motor (kW)</span>
              </div>
            </div>
          </div>

          <div className="chart-canvas-wrap">
            {powertrainChartData && <Line data={powertrainChartData} options={createBaseChartOptions('Power (kW)', -360, 420)} />}
          </div>
        </div>

        {/* GRAPH 4: Energy & Tire Thermals */}
        <div className="chart-card">
          <div className="chart-header">
            <div className="chart-title-wrap">
              <div className="chart-title" style={{ color: '#14b8a6' }}>
                <Battery size={20} /> 4. Battery State of Charge & Tire Surface Thermals
              </div>
              <div className="chart-subtitle">
                Battery percentage (%) along the lap and tire surface temperature (°C).
              </div>
            </div>

            {/* SEPARATE DEDICATED LEGEND FOR GRAPH 4 */}
            <div className="chart-legend">
              <div className="legend-item" style={{ borderColor: '#14b8a6' }}>
                <span className="legend-line" style={{ background: '#14b8a6' }}></span>
                <span style={{ color: '#14b8a6' }}>Battery Charge Level (%)</span>
              </div>
              <div className="legend-item" style={{ borderColor: '#f43f5e' }}>
                <span className="legend-dot" style={{ background: '#f43f5e' }}></span>
                <span style={{ color: '#f43f5e' }}>Tire Surface Temp (°C)</span>
              </div>
            </div>
          </div>

          <div className="chart-canvas-wrap">
            {energyTireChartData && <Line data={energyTireChartData} options={createBaseChartOptions('Level (% / °C)', 0, 130)} />}
          </div>
        </div>

        {/* GRAPH 5: Axle Vertical Loads in kg */}
        <div className="chart-card">
          <div className="chart-header">
            <div className="chart-title-wrap">
              <div className="chart-title" style={{ color: '#38bdf8' }}>
                <Wind size={20} /> 5. Dynamic Axle Vertical Loads & Aerodynamic Downforce
              </div>
              <div className="chart-subtitle">
                Loads and downforce explicitly shown in kilograms (kg) for easy real-world understanding.
              </div>
            </div>

            {/* SEPARATE DEDICATED LEGEND FOR GRAPH 5 */}
            <div className="chart-legend">
              <div className="legend-item" style={{ borderColor: '#38bdf8' }}>
                <span className="legend-line" style={{ background: '#38bdf8' }}></span>
                <span style={{ color: '#38bdf8' }}>Front Axle Load (kg)</span>
              </div>
              <div className="legend-item" style={{ borderColor: '#ec4899' }}>
                <span className="legend-line" style={{ background: '#ec4899' }}></span>
                <span style={{ color: '#ec4899' }}>Rear Axle Load (kg)</span>
              </div>
              <div className="legend-item" style={{ borderColor: '#eab308' }}>
                <span className="legend-dot" style={{ background: '#eab308' }}></span>
                <span style={{ color: '#eab308' }}>Aerodynamic Downforce (kg)</span>
              </div>
            </div>
          </div>

          <div className="chart-canvas-wrap">
            {loadChartData && <Line data={loadChartData} options={createBaseChartOptions('Vertical Load (kg)', 0, undefined)} />}
          </div>
        </div>
      </section>

      {/* 8. Plain-English Knowledge Guide for Fans & Beginners */}
      <section className="chart-card" style={{ marginTop: 24 }}>
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 800, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <HelpCircle size={18} color="#00ff88" /> Plain-English Guide: How 2026 Formula 1 Cars Work
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, fontSize: 13, color: '#d1d5db', lineHeight: 1.6 }}>
          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 14, borderRadius: 10 }}>
            <strong style={{ color: '#00ff88', display: 'block', marginBottom: 4 }}>⚡ The 50/50 Power Split</strong>
            Unlike 2024 cars (which relied primarily on gas), 2026 cars get half their power from the 1.6L petrol engine (400 kW / 536 hp) and half from the electric motor (350 kW / 470 hp) — totaling over 1,000 hp!
          </div>

          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 14, borderRadius: 10 }}>
            <strong style={{ color: '#00e5ff', display: 'block', marginBottom: 4 }}>💨 Active Wing Aerodynamics</strong>
            DRS is replaced by active front and rear wings. In corners, wings stay in high-downforce "Z-Mode" to grip the road. On straights, wings switch to low-drag "X-Mode" to fly past 340 km/h.
          </div>

          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 14, borderRadius: 10 }}>
            <strong style={{ color: '#f59e0b', display: 'block', marginBottom: 4 }}>📉 Smart Electric Tapering</strong>
            If the battery pushed 350 kW continuously, it would run out in 15 seconds. The electric motor delivers full boost up to 290 km/h, then automatically tapers down, allowing the petrol engine to handle top speed.
          </div>

          <div style={{ background: 'rgba(0,0,0,0.25)', padding: 14, borderRadius: 10 }}>
            <strong style={{ color: '#a855f7', display: 'block', marginBottom: 4 }}>🔋 Free Brake Energy Recovery</strong>
            Whenever the driver hits the brakes, the electric motor turns into a high-powered 350 kW generator, capturing kinetic energy and recharging the battery for the very next straightaway.
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="app-footer">
        FIA Formula 1 World Championship 2026 Regulation Simulator & Official 2024 Historical Pole Telemetry Database.
      </footer>
    </div>
  );
}
