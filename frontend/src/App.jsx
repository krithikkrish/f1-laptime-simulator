import React, { useState, useEffect, useMemo } from 'react';
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
  BatteryCharging,
  Flag,
  Activity,
  Play,
  Pause,
  SlidersHorizontal,
  Wind,
  Layers,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Award,
  Fuel,
  Timer,
  TrendingUp,
  TrendingDown,
  Download,
  Settings2,
  Cpu,
  Disc,
  Compass,
  CheckCircle2,
  Flame
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

// High-fidelity natural Chart styling
const createEmberChartOptions = (yTitle, yMin = undefined, yMax = undefined) => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 200 },
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
      padding: 10,
      cornerRadius: 6,
      bodyFont: { family: 'Source Sans 3', size: 13 },
      titleFont: { family: 'Fira Code', size: 12, weight: 'bold' }
    }
  },
  scales: {
    x: {
      grid: { color: '#F5F5F4' },
      ticks: {
        color: '#78716C',
        font: { family: 'Fira Code', size: 11 },
        maxTicksLimit: 9,
        callback: (val) => `${Math.round(val)}m`
      },
      title: {
        display: true,
        text: 'Circuit Distance (Meters)',
        color: '#78716C',
        font: { family: 'Source Sans 3', size: 11.5, weight: '600' }
      }
    },
    y: {
      min: yMin,
      max: yMax,
      grid: { color: '#F5F5F4' },
      ticks: {
        color: '#57534E',
        font: { family: 'Fira Code', size: 11 }
      },
      title: {
        display: true,
        text: yTitle,
        color: '#1C1917',
        font: { family: 'Source Sans 3', size: 11.5, weight: '600' }
      }
    }
  }
});

// Official 2026 FIA Baseline Homologated Defaults
const OFFICIAL_2026_DEFAULTS = {
  ice_kw: 400.0,      // 536 bhp
  mguk_kw: 350.0,     // 470 bhp
  v_taper: 290.0,     // km/h
  v_cutoff: 345.0,    // km/h
  cl_z: 4.80,         // Z-Mode high downforce
  cd_x: 0.85,         // X-Mode low drag
  bbw_bias: 56.5,     // % Front brake bias
  soc_init: 100.0,    // % Initial battery charge
  fuel_kg: 25.0       // Qualifying fuel
};

export default function App() {
  const [tracks, setTracks] = useState([]);
  const [selectedTrackKey, setSelectedTrackKey] = useState('monza');
  const [compound, setCompound] = useState('Soft Slick');
  const [fuelKg, setFuelKg] = useState(25.0);
  const [setupMode, setSetupMode] = useState('balanced');

  // Advanced Engineering Calibration Levers
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [iceKw, setIceKw] = useState(OFFICIAL_2026_DEFAULTS.ice_kw);
  const [mgukKw, setMgukKw] = useState(OFFICIAL_2026_DEFAULTS.mguk_kw);
  const [vTaper, setVTaper] = useState(OFFICIAL_2026_DEFAULTS.v_taper);
  const [vCutoff, setVCutoff] = useState(OFFICIAL_2026_DEFAULTS.v_cutoff);
  const [clZ, setClZ] = useState(OFFICIAL_2026_DEFAULTS.cl_z);
  const [cdX, setCdX] = useState(OFFICIAL_2026_DEFAULTS.cd_x);
  const [bbwBias, setBbwBias] = useState(OFFICIAL_2026_DEFAULTS.bbw_bias);
  const [socInit, setSocInit] = useState(OFFICIAL_2026_DEFAULTS.soc_init);

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

  // 2. Execute 100 Hz Transient Simulation
  const runSimulation = () => {
    if (!selectedTrackKey) return;
    setLoading(true);
    setError(null);

    fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        track_key: selectedTrackKey,
        compound,
        fuel_kg: fuelKg,
        setup: setupMode,
        ice_kw: iceKw,
        mguk_kw: mgukKw,
        v_taper: vTaper,
        v_cutoff: vCutoff,
        cl_z: clZ,
        cd_x: cdX,
        bbw_bias: bbwBias,
        soc_init: socInit / 100.0
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
  };

  // Re-run simulation when track, compound, fuel, or preset changes
  useEffect(() => {
    runSimulation();
  }, [selectedTrackKey, compound, fuelKg, setupMode]);

  // Reset all levers to official 2026 FIA regulations
  const handleResetToBaseline = () => {
    setIceKw(OFFICIAL_2026_DEFAULTS.ice_kw);
    setMgukKw(OFFICIAL_2026_DEFAULTS.mguk_kw);
    setVTaper(OFFICIAL_2026_DEFAULTS.v_taper);
    setVCutoff(OFFICIAL_2026_DEFAULTS.v_cutoff);
    setClZ(OFFICIAL_2026_DEFAULTS.cl_z);
    setCdX(OFFICIAL_2026_DEFAULTS.cd_x);
    setBbwBias(OFFICIAL_2026_DEFAULTS.bbw_bias);
    setSocInit(OFFICIAL_2026_DEFAULTS.soc_init);
    setFuelKg(OFFICIAL_2026_DEFAULTS.fuel_kg);
    setCompound('Soft Slick');
    setSetupMode('balanced');
  };

  // Export MoTeC CSV
  const handleExportMotec = () => {
    fetch('/api/export_motec', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        track_key: selectedTrackKey,
        compound,
        fuel_kg: fuelKg,
        setup: setupMode,
        ice_kw: iceKw,
        mguk_kw: mgukKw,
        v_taper: vTaper,
        v_cutoff: vCutoff,
        cl_z: clZ,
        cd_x: cdX,
        bbw_bias: bbwBias,
        soc_init: socInit / 100.0
      })
    })
      .then(res => res.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `f1_2026_${selectedTrackKey}_motec.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch(err => {
        console.error('Export error:', err);
      });
  };

  // Drive car along circuit
  useEffect(() => {
    if (!isPlaying || !simData?.track?.length_m) return;
    const trackLen = simData.track.length_m;
    const interval = setInterval(() => {
      setScrubDist(prev => (prev + 35) % trackLen);
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

  const liveSpeedKmh = telem?.speed_2026?.[currentIdx] ?? 0;
  const liveSpeedMph = Math.round(liveSpeedKmh * 0.621371);
  const liveGear = telem?.gear?.[currentIdx] ?? 1;
  const liveThrottle = Math.round(telem?.throttle?.[currentIdx] ?? 0);
  const liveBrake = Math.round(telem?.brake?.[currentIdx] ?? 0);
  const liveMguKw = Math.round(telem?.p_mguk_kw?.[currentIdx] ?? 0);
  const isAeroXMode = liveSpeedKmh > 260 && liveThrottle > 90;
  const livePoleSpeedKmh = telem?.speed_2025?.[currentIdx] ?? null;
  const liveSpeedDelta = livePoleSpeedKmh !== null ? Math.round(liveSpeedKmh - livePoleSpeedKmh) : null;

  // Track Phase Inspector logic
  const currentTrackPhase = useMemo(() => {
    if (!simData?.track?.length_m) return { name: 'Starting Grid', type: 'straight', sector: 'Sector 1' };
    
    const pct = (scrubDist / trackLen) * 100;
    let sector = 'Sector 1';
    if (pct > 66.6) sector = 'Sector 3';
    else if (pct > 33.3) sector = 'Sector 2';
    
    if (simData.sectors && simData.sectors.length >= 3) {
      if (scrubDist < simData.sectors[0].end) sector = simData.sectors[0].name;
      else if (scrubDist < simData.sectors[1].end) sector = simData.sectors[1].name;
      else sector = simData.sectors[2].name;
    }

    let name = 'Corner Acceleration Phase';
    let type = 'accel';

    if (liveBrake > 15) {
      name = 'Heavy Braking & Energy Regeneration';
      type = 'brake';
    } else if (isAeroXMode) {
      name = 'Top-Speed Straightaway (X-Mode Low Drag)';
      type = 'straight';
    } else if (liveSpeedKmh < 165 && liveThrottle < 85) {
      name = 'Technical Corner Apex (Z-Mode Downforce)';
      type = 'corner';
    } else if (liveThrottle > 75) {
      name = 'Corner Exit +470 HP Electric Torque';
      type = 'boost';
    }

    return { name, type, sector };
  }, [scrubDist, trackLen, liveBrake, isAeroXMode, liveSpeedKmh, liveThrottle, simData]);

  // Dynamic Multi-Color Speed Ribbon Gradient across the entire circuit
  const speedRibbonGradient = useMemo(() => {
    if (!telem?.speed_2026 || telem.speed_2026.length === 0) return '';
    const speeds = telem.speed_2026;
    const stops = speeds.map((v, i) => {
      const pct = ((i / (speeds.length - 1)) * 100).toFixed(1);
      let color = '#4338CA'; // Indigo: slow apex (< 135 km/h)
      if (v >= 285) color = '#C2410C'; // Terracotta: top speed (> 285 km/h)
      else if (v >= 215) color = '#D97706'; // Amber: high speed (215 - 285 km/h)
      else if (v >= 135) color = '#0284C7'; // Cyan: medium corner (135 - 215 km/h)
      return `${color} ${pct}%`;
    });
    return `linear-gradient(to right, ${stops.join(', ')})`;
  }, [telem]);

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
        label: '2026 Simulation Car',
        data: telem.speed_2026,
        borderColor: '#C2410C', // Terracotta
        backgroundColor: 'rgba(194, 65, 12, 0.06)',
        borderWidth: 2.6,
        tension: 0.2,
        pointRadius: 0,
        fill: true,
      }
    ];

    if (telem.speed_2025) {
      datasets.push({
        label: `2025 Pole (${simData.pole_benchmark.driver_name})`,
        data: telem.speed_2025,
        borderColor: '#0284C7', // Cyan/Slate
        borderWidth: 1.8,
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
          borderColor: '#16A34A',
          borderWidth: 1.8,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Brake Pressure (%)',
          data: telem.brake,
          borderColor: '#DC2626',
          borderWidth: 1.8,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Gear (x12.5)',
          data: telem.gear.map(g => g * 12.5),
          borderColor: '#D97706',
          borderWidth: 1.6,
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
          label: 'V6 Combustion Engine (kW)',
          data: telem.p_ice_kw,
          borderColor: '#EA580C',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Electric MGU-K Motor (kW)',
          data: telem.p_mguk_kw,
          borderColor: '#7C3AED',
          backgroundColor: 'rgba(124, 58, 237, 0.06)',
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
        }
      ]
    };
  }, [telem]);

  // ==========================================
  // CHART 4: BATTERY & TIRE THERMALS
  // ==========================================
  const energyTireChartData = useMemo(() => {
    if (!telem) return null;
    return {
      labels: telem.distance,
      datasets: [
        {
          label: 'Battery State of Charge (%)',
          data: telem.soc_pct,
          borderColor: '#0D9488',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Tire Surface Temp (°C)',
          data: telem.tire_temp,
          borderColor: '#E11D48',
          borderWidth: 2,
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
          label: 'Front Dynamic Load (kg)',
          data: telem.front_load_kg,
          borderColor: '#0284C7',
          borderWidth: 1.8,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Rear Dynamic Load (kg)',
          data: telem.rear_load_kg,
          borderColor: '#DB2777',
          borderWidth: 1.8,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Aerodynamic Downforce (kg)',
          data: telem.downforce_kg,
          borderColor: '#CA8A04',
          borderWidth: 1.8,
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
      {/* 1. Sidebar Navigation */}
      <aside className="ember-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand-title">
            <div className="brand-icon-wrapper">
              <Gauge size={18} />
            </div>
            <span>Ember Studio</span>
          </div>
          <div className="sidebar-brand-subtitle">
            Formula 1 Vehicle Dynamics Lab
          </div>
        </div>

        <div className="sidebar-content">
          <div className="sidebar-section-title">2025 CALENDAR CIRCUITS</div>
          {tracks.map(t => (
            <div
              key={t.key}
              className={`sidebar-nav-item ${selectedTrackKey === t.key ? 'active' : ''}`}
              onClick={() => setSelectedTrackKey(t.key)}
            >
              <div className="nav-track-label">
                <span className="country-code-badge">{t.country_code || 'GP'}</span>
                <span>{t.short_name}</span>
              </div>
              <span style={{ fontSize: 11, fontFamily: 'var(--font-code)', color: 'var(--neutral)' }}>
                {Math.round(t.length_m / 1000 * 10) / 10}k
              </span>
            </div>
          ))}

          <div className="sidebar-section-title" style={{ marginTop: 20 }}>SOLVER STATUS</div>
          <div style={{ padding: '6px 10px', fontSize: 13, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
            <CheckCircle2 size={14} /> 100 Hz Forward-Euler
          </div>
          <div style={{ padding: '0 10px', fontSize: 12, color: 'var(--neutral)' }}>
            2025 FIA Benchmark Ground-Truth
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
            <span>Championship Dynamics</span>
            <span>/</span>
            <strong>{activeTrackMeta?.country} Grand Prix ({activeTrackMeta?.short_name})</strong>
          </div>

          <div className="topbar-badge">
            <Award size={13} /> 2025 Championship Benchmark
          </div>
        </header>

        {/* Content Container (Natural editorial flow, unboxed) */}
        <div className="ember-container">
          {/* Natural Editorial Page Header */}
          <div className="page-header">
            <div className="header-meta-row">
              <span className="venue-country-pill">
                <Compass size={12} /> {activeTrackMeta?.country_code || 'GP'}
              </span>
              <span style={{ fontSize: 13, color: 'var(--neutral)' }}>
                FIA World Championship Circuit • {Math.round(trackLen).toLocaleString()} Meters
              </span>
            </div>
            <h1 className="display-title">
              {simData?.track?.name || 'Grand Prix Circuit'}
            </h1>
            <p className="section-desc" style={{ marginTop: 6 }}>
              Forward-Euler vehicle dynamics simulation analyzing 2026 regulations against authentic 2025 qualifying pole positions.
            </p>
          </div>

          {/* Natural Editorial Benchmark Callout (No chunky box!) */}
          {simData?.pole_benchmark && (
            <div className="editorial-benchmark-strip">
              <div className="benchmark-info-group">
                <span className="benchmark-tag">
                  <Flag size={13} /> Official 2025 Saturday Qualifying Reference
                </span>
                <div className="benchmark-headline">
                  Pole Sitter: <strong>{simData.pole_benchmark.driver_name}</strong> ({simData.pole_benchmark.team_name})
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--neutral)' }}>
                  Sourced from official OpenF1 / FastF1 telemetry timing sectors.
                </div>
              </div>

              <div className="benchmark-time-badge">
                <div className="benchmark-time-label">2025 Pole Benchmark</div>
                <div className="benchmark-time-val">{simData.pole_benchmark.lap_time_str}</div>
              </div>
            </div>
          )}

          {/* Natural Controls Bar (Sitting inline on page canvas) */}
          <div className="natural-controls-bar">
            {/* Tire Compound Chips */}
            <div className="control-item">
              <div className="control-item-label">
                <Disc size={13} /> Tire Compound
              </div>
              <div className="chip-group">
                {[
                  { id: 'Soft Slick', pip: 'soft', label: 'Soft Slick' },
                  { id: 'Medium Slick', pip: 'medium', label: 'Medium Slick' },
                  { id: 'Hard Slick', pip: 'hard', label: 'Hard Slick' },
                  { id: 'Wet Weather', pip: 'wet', label: 'Wet Tread' },
                ].map(c => (
                  <button
                    key={c.id}
                    className={`ember-chip ${compound === c.id ? 'active' : ''}`}
                    onClick={() => setCompound(c.id)}
                  >
                    <span className={`tire-pip ${c.pip}`} />
                    <span>{c.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Fuel Load Chips */}
            <div className="control-item">
              <div className="control-item-label">
                <Fuel size={13} /> Fuel Load
              </div>
              <div className="chip-group">
                {[
                  { kg: 25.0, label: 'Quali (25 kg)', icon: Timer },
                  { kg: 50.0, label: 'Sprint (50 kg)', icon: Activity },
                  { kg: 100.0, label: 'Grand Prix (100 kg)', icon: Flag },
                ].map(f => {
                  const Icon = f.icon;
                  return (
                    <button
                      key={f.kg}
                      className={`ember-chip ${fuelKg === f.kg ? 'active' : ''}`}
                      onClick={() => setFuelKg(f.kg)}
                    >
                      <Icon size={12} />
                      <span>{f.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Aero Trim Chips */}
            <div className="control-item">
              <div className="control-item-label">
                <Wind size={13} /> Aero Trim
              </div>
              <div className="chip-group">
                {[
                  { id: 'balanced', label: 'Balanced Spec', icon: Layers },
                  { id: 'high_speed', label: 'Monza Low-Drag', icon: Wind },
                  { id: 'high_downforce', label: 'Monaco High-Grip', icon: SlidersHorizontal },
                ].map(s => {
                  const Icon = s.icon;
                  return (
                    <button
                      key={s.id}
                      className={`ember-chip ${setupMode === s.id ? 'active' : ''}`}
                      onClick={() => setSetupMode(s.id)}
                    >
                      <Icon size={12} />
                      <span>{s.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Action Buttons: Advanced Calibration Toggle */}
            <div className="controls-actions-group">
              <button
                className={`ember-btn-ghost ${showAdvanced ? 'active' : ''}`}
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                <SlidersHorizontal size={14} />
                <span>Advanced Calibration</span>
                {showAdvanced ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </button>

              <button
                className="ember-btn-primary"
                onClick={runSimulation}
                title="Run 100 Hz simulation"
              >
                <Play size={13} fill="currentColor" />
                <span>Simulate</span>
              </button>
            </div>
          </div>

          {/* Advanced Engineering Calibration Panel (Only rendered when requested) */}
          {showAdvanced && (
            <div className="advanced-drawer">
              <div className="drawer-header">
                <div>
                  <div className="drawer-title">
                    <Cpu size={18} color="var(--primary)" />
                    <span>Advanced Powertrain & Chassis Calibration</span>
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--neutral)', marginTop: 2 }}>
                    Tune individual 2026 power units, active aerodynamic downforce levels, and brake bias balance.
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="ember-btn-ghost"
                    style={{ fontSize: 12, padding: '5px 10px' }}
                    onClick={handleResetToBaseline}
                  >
                    <RotateCcw size={12} />
                    <span>Reset to 2026 Baseline</span>
                  </button>

                  <button
                    className="ember-btn-ghost"
                    style={{ fontSize: 12, padding: '5px 10px' }}
                    onClick={handleExportMotec}
                  >
                    <Download size={12} />
                    <span>Export MoTeC CSV</span>
                  </button>
                </div>
              </div>

              <div className="advanced-grid">
                {/* ICE Power Slider */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">1.6L V6 ICE Power</span>
                    <span className="slider-val">{Math.round(iceKw)} kW ({Math.round(iceKw * 1.34102)} bhp)</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="300"
                    max="550"
                    step="5"
                    value={iceKw}
                    onChange={e => setIceKw(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Official 2026 Cap: 400 kW (~536 bhp)</span>
                </div>

                {/* MGU-K Power Slider */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">350 kW Electric MGU-K</span>
                    <span className="slider-val">{Math.round(mgukKw)} kW (+{Math.round(mgukKw * 1.34102)} hp)</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="150"
                    max="450"
                    step="5"
                    value={mgukKw}
                    onChange={e => setMgukKw(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Official 2026 Split: 350 kW (+470 hp)</span>
                </div>

                {/* MGU-K Taper Onset */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">Electric Taper Onset</span>
                    <span className="slider-val">{Math.round(vTaper)} km/h</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="220"
                    max="320"
                    step="5"
                    value={vTaper}
                    onChange={e => setVTaper(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Baseline speed where electric power tapers down</span>
                </div>

                {/* MGU-K Full Cutoff */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">Electric Full Cutoff</span>
                    <span className="slider-val">{Math.round(vCutoff)} km/h</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="300"
                    max="370"
                    step="5"
                    value={vCutoff}
                    onChange={e => setVCutoff(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Velocity above which ICE delivers 100% propulsion</span>
                </div>

                {/* Downforce (Z-Mode) */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">Cornering Cl·A (Z-Mode)</span>
                    <span className="slider-val">{clZ.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="2.5"
                    max="6.5"
                    step="0.05"
                    value={clZ}
                    onChange={e => setClZ(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Higher value gives faster apex cornering grip</span>
                </div>

                {/* Drag (X-Mode) */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">Straight Drag Cd·A (X-Mode)</span>
                    <span className="slider-val">{cdX.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="0.5"
                    max="1.5"
                    step="0.02"
                    value={cdX}
                    onChange={e => setCdX(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Low-drag active aero state on straightaways</span>
                </div>

                {/* Brake Bias */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">Brake Bias (Front %)</span>
                    <span className="slider-val">{bbwBias.toFixed(1)}%</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="50.0"
                    max="65.0"
                    step="0.5"
                    value={bbwBias}
                    onChange={e => setBbwBias(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Static hydraulic bias before dynamic BBW migration</span>
                </div>

                {/* Battery Initial SoC */}
                <div className="slider-group">
                  <div className="slider-header">
                    <span className="slider-label">Starting Battery SoC</span>
                    <span className="slider-val">{Math.round(socInit)}%</span>
                  </div>
                  <input
                    type="range"
                    className="ember-slider"
                    min="20"
                    max="100"
                    step="5"
                    value={socInit}
                    onChange={e => setSocInit(parseFloat(e.target.value))}
                  />
                  <span style={{ fontSize: 11, color: 'var(--neutral)' }}>Starting state of charge out of the final pit lane exit</span>
                </div>
              </div>

              <div className="drawer-footer-actions">
                <button
                  className="ember-btn-primary"
                  onClick={runSimulation}
                >
                  <Play size={13} fill="currentColor" />
                  <span>Apply & Simulate Calibration</span>
                </button>
              </div>
            </div>
          )}

          {/* Natural Editorial Verdict & Delta (Unboxed) */}
          {simData?.results && (
            <div className="editorial-verdict-section">
              <div className="verdict-lap-col">
                <span className="verdict-eyebrow">Simulated 2026 Lap Time</span>
                <div className="verdict-laptime-text">{simData.results.lap_time_str}</div>

                {simData.results.delta_s !== null && (
                  <div className={`verdict-delta-tag ${simData.results.faster_than_pole ? 'faster' : 'slower'}`}>
                    {simData.results.faster_than_pole ? (
                      <>
                        <TrendingUp size={14} />
                        <span>{Math.abs(simData.results.delta_s).toFixed(3)}s faster than 2025 pole</span>
                      </>
                    ) : (
                      <>
                        <Timer size={14} />
                        <span>+{simData.results.delta_s.toFixed(3)}s vs 2025 pole lap</span>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div className="verdict-narrative">
                <p>
                  <strong>Race Engineering Analysis:</strong> {simData.results.faster_than_pole
                    ? `The 2026 specification vehicle eclipses ${simData.pole_benchmark.driver_name}'s 2025 pole time by ${Math.abs(simData.results.delta_s).toFixed(3)} seconds. The combination of low-drag X-Mode active aerodynamics and instantaneous +470 hp electric torque out of corner apexes produces superior terminal speed.`
                    : `The 2026 regulation car is +${simData.results.delta_s.toFixed(3)} seconds off the 2025 pole reference. With higher cornering mass (888 kg) and lower floor downforce under the revised rules, mechanical grip through technical medium-speed turns remains the determining lap-time factor.`}
                </p>
              </div>
            </div>
          )}

          {/* Natural Four Metrics (Horizontal strip with fine hairlines, NO gray boxes) */}
          {simData?.results && (
            <div className="natural-metrics-strip">
              <div className="metric-strip-item">
                <span className="metric-strip-title" style={{ color: 'var(--primary)' }}>
                  <Activity size={13} /> 2026 Lap Time
                </span>
                <div className="metric-strip-value" style={{ color: 'var(--primary)' }}>
                  {simData.results.lap_time_str}
                </div>
                <div className="metric-strip-sub">
                  2025 Benchmark: <strong>{simData.pole_benchmark.lap_time_str}</strong> ({simData.pole_benchmark.driver_name})
                </div>
              </div>

              <div className="metric-strip-item">
                <span className="metric-strip-title" style={{ color: '#0284C7' }}>
                  <Gauge size={13} /> Straightaway Peak
                </span>
                <div className="metric-strip-value">
                  {Math.round(simData.results.top_speed_kmh)} <span style={{ fontSize: 14 }}>km/h</span>
                </div>
                <div className="metric-strip-sub">
                  <strong>{Math.round(simData.results.top_speed_mph)} mph</strong> in X-Mode (2025: {simData.pole_benchmark.top_speed_kmh} km/h)
                </div>
              </div>

              <div className="metric-strip-item">
                <span className="metric-strip-title" style={{ color: 'var(--accent)' }}>
                  <Zap size={13} /> Electric Boost
                </span>
                <div className="metric-strip-value" style={{ color: 'var(--accent)' }}>
                  350 kW <span style={{ fontSize: 14 }}>(+470 HP)</span>
                </div>
                <div className="metric-strip-sub">
                  50/50 powertrain split delivering peak corner exit acceleration
                </div>
              </div>

              <div className="metric-strip-item">
                <span className="metric-strip-title" style={{ color: 'var(--success)' }}>
                  <BatteryCharging size={13} /> Energy Harvested
                </span>
                <div className="metric-strip-value">
                  {simData.results.energy_regen_mj.toFixed(2)} <span style={{ fontSize: 14 }}>MJ</span>
                </div>
                <div className="metric-strip-sub">
                  Finish Battery SoC: <strong>{Math.round(simData.results.battery_finish_soc)}%</strong> under heavy braking
                </div>
              </div>
            </div>
          )}

          {/* Interactive Circuit Map & Cockpit Telemetry (Boxes used properly for Canvas) */}
          <div className="visualizer-section">
            {/* Left: Scaled Circuit Map */}
            <div className="canvas-frame">
              <div className="canvas-frame-header">
                <div className="canvas-frame-title">
                  <Compass size={17} color="var(--primary)" />
                  <span>{simData?.track?.name || 'Circuit'}</span>
                </div>

                <button
                  className="ember-btn-primary"
                  style={{ padding: '6px 12px', fontSize: 12.5 }}
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? <Pause size={13} /> : <Play size={13} fill="currentColor" />}
                  <span>{isPlaying ? 'Pause' : 'Drive Lap'}</span>
                </button>
              </div>

              <div className="track-svg-box">
                {mapSvgData && (
                  <svg className="track-svg" viewBox={mapSvgData.viewBox}>
                    <path
                      d={mapSvgData.pathStr}
                      fill="none"
                      stroke="#E7E5E4"
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
                        <circle r="16" fill="rgba(194, 65, 12, 0.2)" />
                        <circle r="8" fill="#C2410C" stroke="#FFFFFF" strokeWidth="2" />
                      </g>
                    )}
                  </svg>
                )}
              </div>

              {/* Circuit Speed Bar & Phase Inspector */}
              <div className="track-speedbar-section">
                {/* Phase Inspector Header */}
                <div className="phase-inspector-bar">
                  <div className="phase-badge-group">
                    <span className="sector-indicator-pill">{currentTrackPhase.sector}</span>
                    <span className="phase-name-badge">
                      {currentTrackPhase.type === 'brake' && <Activity size={13} color="#DC2626" />}
                      {currentTrackPhase.type === 'straight' && <Wind size={13} color="#C2410C" />}
                      {currentTrackPhase.type === 'corner' && <Compass size={13} color="#0284C7" />}
                      {currentTrackPhase.type === 'boost' && <Zap size={13} color="#D97706" />}
                      {currentTrackPhase.type === 'accel' && <Flame size={13} color="#C2410C" />}
                      <span>{currentTrackPhase.name}</span>
                    </span>
                  </div>

                  {/* Speed Comparison at this Track Phase */}
                  <div className="phase-speed-comparison">
                    <span>2026: <strong className="phase-speed-val">{Math.round(liveSpeedKmh)} km/h</strong></span>
                    {livePoleSpeedKmh !== null && (
                      <>
                        <span style={{ color: 'var(--neutral)' }}>|</span>
                        <span style={{ color: '#0284C7' }}>2025 Pole: <strong>{Math.round(livePoleSpeedKmh)} km/h</strong></span>
                        <span className={`phase-delta-tag ${liveSpeedDelta >= 0 ? 'faster' : 'slower'}`}>
                          {liveSpeedDelta >= 0 ? `+${liveSpeedDelta}` : liveSpeedDelta} km/h
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Continuous Multi-Color Speed Ribbon (Heatmap across track) */}
                <div
                  className="speed-ribbon-wrapper"
                  onClick={e => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const clickX = e.clientX - rect.left;
                    const pct = Math.max(0, Math.min(1, clickX / rect.width));
                    setScrubDist(pct * trackLen);
                    if (isPlaying) setIsPlaying(false);
                  }}
                  title="Click anywhere to inspect car speed at that track phase"
                >
                  <div
                    className="speed-ribbon-track"
                    style={{ background: speedRibbonGradient || '#C2410C' }}
                  >
                    {/* Sector Dividers (S1 / S2 / S3) */}
                    {simData?.sectors?.slice(0, 2).map((sec, sIdx) => {
                      const divPct = (sec.end / trackLen) * 100;
                      return (
                        <div
                          key={sIdx}
                          className="speed-ribbon-sector-divider"
                          style={{ left: `${divPct}%` }}
                          title={`Boundary: ${sec.name}`}
                        />
                      );
                    })}
                  </div>

                  {/* Active Position Tracking Needle */}
                  <div
                    className="speed-ribbon-needle"
                    style={{ left: `${Math.min(100, Math.max(0, (scrubDist / trackLen) * 100))}%` }}
                  />
                </div>

                {/* Speed Ribbon Legend & Sector Ticks */}
                <div className="speed-ribbon-legend">
                  <div className="legend-speed-stops">
                    <span className="speed-stop-item">
                      <span className="speed-stop-color" style={{ backgroundColor: '#4338CA' }} />
                      <span>&lt; 135 Slow Apex</span>
                    </span>
                    <span className="speed-stop-item">
                      <span className="speed-stop-color" style={{ backgroundColor: '#0284C7' }} />
                      <span>135-215 Mid Turn</span>
                    </span>
                    <span className="speed-stop-item">
                      <span className="speed-stop-color" style={{ backgroundColor: '#D97706' }} />
                      <span>215-285 High Speed</span>
                    </span>
                    <span className="speed-stop-item">
                      <span className="speed-stop-color" style={{ backgroundColor: '#C2410C' }} />
                      <span>&gt; 285 Straight Peak</span>
                    </span>
                  </div>

                  <span style={{ fontFamily: 'var(--font-code)' }}>
                    Track Speed Ribbon
                  </span>
                </div>
              </div>

              {/* Scrubber slider */}
              <div className="scrub-wrapper">
                <div className="scrub-labels">
                  <span>Start (0 m)</span>
                  <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Distance: {Math.round(scrubDist)} m</span>
                  <span>Finish ({Math.round(trackLen)} m)</span>
                </div>
                <input
                  type="range"
                  className="scrub-slider"
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

            {/* Right: Cockpit Telemetry Display */}
            <div className="cockpit-view">
              <div className="cockpit-header-title">
                <Settings2 size={14} /> Telemetry HUD
              </div>

              {/* Instantaneous Speed Bar Gauge */}
              <div className="cockpit-speedbar-block">
                <div className="cockpit-speedbar-header">
                  <span style={{ color: 'var(--neutral)', fontWeight: 600 }}>Phase Velocity Fill</span>
                  <span style={{ fontFamily: 'var(--font-code)', fontSize: 11 }}>
                    <strong style={{ color: 'var(--primary)' }}>{Math.round(liveSpeedKmh)} km/h</strong>
                    {livePoleSpeedKmh && <span style={{ color: '#0284C7', marginLeft: 6 }}>({Math.round(livePoleSpeedKmh)} pole)</span>}
                  </span>
                </div>
                <div className="speedbar-gauge-track">
                  <div
                    className="speedbar-gauge-fill"
                    style={{ width: `${Math.min(100, Math.max(0, (liveSpeedKmh / 365) * 100))}%` }}
                  />
                  {livePoleSpeedKmh && (
                    <div
                      className="speedbar-ghost-needle"
                      style={{ left: `${Math.min(100, Math.max(0, (livePoleSpeedKmh / 365) * 100))}%` }}
                      title={`2025 Pole Speed at this phase: ${Math.round(livePoleSpeedKmh)} km/h`}
                    />
                  )}
                </div>
                <div className="speedbar-ticks">
                  <span>0</span>
                  <span>100</span>
                  <span>200</span>
                  <span>300</span>
                  <span>365 km/h</span>
                </div>
              </div>

              <div className="cockpit-telemetry-readouts">
                <div className="hud-readout-col">
                  <div className="hud-label">Live Velocity</div>
                  <div className="hud-number">
                    {Math.round(liveSpeedKmh)} <span className="hud-unit">km/h</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{liveSpeedMph} mph</div>
                </div>

                <div className="hud-readout-col">
                  <div className="hud-label">Transmission</div>
                  <div className="hud-number" style={{ color: 'var(--primary)' }}>
                    Gear {liveGear}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>8-Speed Seamless</div>
                </div>
              </div>

              {/* Pedals */}
              <div>
                <div className="pedal-block">
                  <div className="pedal-label-row">
                    <span>Throttle Pedal</span>
                    <strong style={{ color: 'var(--success)' }}>{liveThrottle}%</strong>
                  </div>
                  <div className="pedal-track">
                    <div className="pedal-fill" style={{ width: `${liveThrottle}%`, backgroundColor: 'var(--success)' }}></div>
                  </div>
                </div>

                <div className="pedal-block">
                  <div className="pedal-label-row">
                    <span>Brake Pressure</span>
                    <strong style={{ color: 'var(--error)' }}>{liveBrake}%</strong>
                  </div>
                  <div className="pedal-track">
                    <div className="pedal-fill" style={{ width: `${liveBrake}%`, backgroundColor: 'var(--error)' }}></div>
                  </div>
                </div>
              </div>

              <div className="cockpit-status-summary">
                <div className="status-row">
                  <span className="status-label"><Zap size={13} /> MGU-K Motor:</span>
                  <strong style={{ color: liveMguKw >= 0 ? 'var(--primary)' : 'var(--success)' }}>
                    {liveMguKw >= 0 ? `+${liveMguKw} kW (Deploying)` : `${liveMguKw} kW (Harvesting)`}
                  </strong>
                </div>
                <div className="status-row">
                  <span className="status-label"><Wind size={13} /> Active Wings:</span>
                  <strong style={{ color: isAeroXMode ? 'var(--primary)' : 'var(--text-primary)' }}>
                    {isAeroXMode ? 'Open (X-Mode Low Drag)' : 'Closed (Z-Mode Downforce)'}
                  </strong>
                </div>
                <div className="status-row">
                  <span className="status-label"><Disc size={13} /> Fitted Compound:</span>
                  <strong>{compound}</strong>
                </div>
              </div>
            </div>
          </div>

          {/* 5 Modular Decongested Telemetry Charts (Separate Legends, 2025 Data Only) */}
          <div className="charts-section">
            <div className="charts-section-header">
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
                    <Gauge size={17} color="var(--primary)" /> 1. Speed Profile & Lap Comparison
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
                    <Activity size={17} color="var(--success)" /> 2. Driver Inputs & Sequential Transmission
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
                    <Zap size={17} color="var(--primary)" /> 3. Hybrid Powertrain Energy Distribution
                  </h3>
                  <span className="chart-subtitle">
                    1.6L V6 Turbo combustion engine (400 kW) vs 350 kW Electric MGU-K motor deployment & harvesting.
                  </span>
                </div>

                <div className="chart-legend-row">
                  <div className="legend-badge">
                    <span className="legend-pill-color" style={{ backgroundColor: '#EA580C' }}></span>
                    <span>1.6L V6 Engine (kW)</span>
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
                    <Battery size={17} color="#0D9488" /> 4. Battery State of Charge & Tire Surface Thermals
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
                    <Wind size={17} color="#0284C7" /> 5. Dynamic Axle Vertical Loads & Aerodynamic Downforce
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
                    <span>Downforce (kg)</span>
                  </div>
                </div>
              </div>

              <div className="chart-viewport">
                {loadChartData && <Line data={loadChartData} options={createEmberChartOptions('Vertical Load (kg)', 0, undefined)} />}
              </div>
            </div>
          </div>

          {/* Educational Technical Spread (Natural editorial columns, unboxed) */}
          <div className="editorial-technical-spread">
            <h3 className="technical-spread-title">
              2026 Technical Regulations Engineering Principles
            </h3>
            <p className="section-desc">
              The 2026 Formula 1 regulations introduce the most comprehensive powertrain and aerodynamic overhaul in championship history.
            </p>

            <div className="technical-columns-grid">
              <div className="technical-column">
                <div className="column-header">
                  <Cpu size={16} color="var(--primary)" />
                  <span>50/50 Power Parity</span>
                </div>
                <p className="column-body">
                  The electric MGU-K output nearly triples from 120 kW to 350 kW (~470 hp), matching the 400 kW (~536 hp) turbocharged 1.6L V6 running on 100% sustainable advanced fuels.
                </p>
              </div>

              <div className="technical-column">
                <div className="column-header">
                  <Wind size={16} color="#0284C7" />
                  <span>Active Aerodynamics</span>
                </div>
                <p className="column-body">
                  Replacing DRS, movable front and rear wings switch automatically between high-downforce Z-Mode through corners and ultra-low drag X-Mode on high-speed straights.
                </p>
              </div>

              <div className="technical-column">
                <div className="column-header">
                  <TrendingDown size={16} color="var(--warning)" />
                  <span>Velocity Tapering</span>
                </div>
                <p className="column-body">
                  To conserve the 4.0 MJ per lap battery quota, maximum 350 kW electrical boost is delivered on corner exit up to 290 km/h, tapering linearly to 0 kW at 345 km/h.
                </p>
              </div>

              <div className="technical-column">
                <div className="column-header">
                  <BatteryCharging size={16} color="var(--success)" />
                  <span>High-Rate Harvesting</span>
                </div>
                <p className="column-body">
                  Heavy braking events recover up to 350 kW through rear-axle regeneration, providing the energy needed to power subsequent corner exit deployments without conventional friction pad wear.
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <footer className="ember-footer">
            Ember Studio • 2026 Formula 1 Forward-Euler Dynamics ODE Solver & 2025 FIA World Championship Pole Benchmark Telemetry.
          </footer>
        </div>
      </main>
    </div>
  );
}
