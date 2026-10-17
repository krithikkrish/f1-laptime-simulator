# 🏎️ 2026 F1 Transient Lap-Time & Dual-Track Vehicle Dynamics Simulator

> **Industrial-grade motorsport simulation workstation** engineering the official 2026 Formula 1 technical regulations at **0.01-second ($dt = 100\text{ Hz}$) Forward-Euler ODE resolution**. Featuring a **4-Wheel Dual-Track chassis model** with dynamic normal load transfer, suspension roll stiffness, Pacejka Magic Formula tire kinematics, an **8-speed seamless-shift sequential gearbox**, active aerodynamics (**Z-Mode** & **X-Mode**), **350 kW MGU-K tapering**, all **24 FIA World Championship Grand Prix circuits**, a **McLaren Applied ATLAS / MoTeC i2 Pro dark workstation UI**, plain-English race engineer telemetry insights, and official **MoTeC i2 Pro & MATLAB R2026a export engines**.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit Workstation](https://img.shields.io/badge/Workstation-Streamlit%201.40%2B-FF4B4B.svg)](https://streamlit.io/)
[![MATLAB R2026a](https://img.shields.io/badge/MATLAB-R2026a%20Suite-0076A8.svg)](https://www.mathworks.com/)
[![MoTeC i2 Pro Compatible](https://img.shields.io/badge/Telemetry-MoTeC%20i2%20Pro-red.svg)](https://www.motec.com.au/)

---

## 🌟 Core Highlights

### 1. Complete 24-Circuit FIA World Championship Calendar
- **Authentic 3D GPS Trajectories & Elevation**: Pre-cached and verified 3D waypoints for all 24 Grand Prix circuits—from high-speed temples like Monza and Spa to tight street labyrinths like Monaco, Singapore, and Baku.
- **Zero Fallback**: Every circuit loads instantaneously with its authentic track geometry, timing sectors (S1, S2, S3), real weather station readings, and real qualifying pole lap benchmarks.
- **24 Circuits Supported**:
  - 🇧🇭 Bahrain (Sakhir) | 🇸🇦 Saudi Arabia (Jeddah) | 🇦🇺 Australia (Melbourne) | 🇯🇵 Japan (Suzuka)
  - 🇨🇳 China (Shanghai) | 🇺🇸 Miami | 🇮🇹 Emilia Romagna (Imola) | 🇲🇨 Monaco (Monte Carlo)
  - 🇨🇦 Canada (Montreal) | 🇪🇸 Spain (Barcelona) | 🇦🇹 Austria (Spielberg) | 🇬🇧 Great Britain (Silverstone)
  - 🇭🇺 Hungary (Hungaroring) | 🇧🇪 Belgium (Spa-Francorchamps) | 🇳🇱 Netherlands (Zandvoort) | 🇮🇹 Italy (Monza)
  - 🇦🇿 Azerbaijan (Baku) | 🇸🇬 Singapore (Marina Bay) | 🇺🇸 United States (Austin) | 🇲🇽 Mexico (Mexico City)
  - 🇧🇷 Brazil (Interlagos) | 🇺🇸 Las Vegas | 🇶🇦 Qatar (Lusail) | 🇦🇪 Abu Dhabi (Yas Marina)

### 2. Authentic 2026 Technical Regulations Defaults with Dynamic Tuning
- **50/50 Power Split**: 400 kW (~536 bhp) internal combustion engine running on 100% sustainable fuels + 350 kW (~470 bhp) electric MGU-K motor (totaling over 1,000 bhp).
- **MGU-K Taper Curve**: Full 350 kW electric boost available on corner exit up to 290 km/h, tapering linearly to 0 kW at 345 km/h to manage the 4.0 MJ per lap battery limit.
- **Active Aerodynamics (Z-Mode & X-Mode)**: High-downforce Z-Mode in cornering and heavy braking vs low-drag X-Mode on straights (~28% drag reduction).
- **Chassis & Minimum Mass**: Homologated 888 kg minimum mass (768 kg empty + 80 kg driver ballast + 40 kg qualifying fuel).
- **Dynamic Engineering Levers**: All parameters default to official 2026 regulations, but remain fully dynamic and tunable via interactive sliders with plain-English tooltips. A one-click **"✨ Reset All to Official 2026 FIA Regulations"** restores homologated baseline specs immediately.

### 3. Dual-Mode Interface: Accessible for Everyone & Pro Engineering
- **🟢 Mode 1: Simple & Clean (Default for Everyone)**:
  - **Hero Lap Result Banner**: Huge 46px font (`1:20.842`), high-contrast delta badge (`🟢 0.630s FASTER THAN REAL POLE!`), and a plain-English explanation comparing the simulated lap against the real qualifying pole driver and team.
  - **4 Decongested Stat Cards**: Lap Time vs Real Pole, Top Speed (km/h & mph on main straights), 350 kW Electric Boost in horsepower (+470 hp), and Battery Health % with energy regenerated in MJ.
  - **Interactive Lap Visualizer**: Clean side-by-side view featuring an interactive track map on the left (with a car scrubbing along the circuit) and a minimalist 4-gauge digital cockpit on the right (Speed, Gear, Throttle/Brake bars, and Motor deploy/recharge state).
  - **High-Contrast Speed Chart**: A single, clean, uncluttered graph showing speed across the lap with straight vs corner annotations.
  - **Plain-English Beginner's Guide**: An easy-to-read collapsible guide explaining 2026 50/50 hybrid power, electric tapering, active aero wings, and regenerative braking.
- **⚙️ Mode 2: Pro Engineering Telemetry (For Race Engineers)**:
  - Full 6-channel MoTeC/ATLAS telemetry graphs (Speed, Throttle/Brake, Gear/RPM, 4-Corner Tire Loads $F_z$, Power Deployment, and Battery SoC).
  - G-G friction circle with peak lateral/longitudinal acceleration callouts.
  - Full FIA technical homologation setup sheet.
  - Export suite for MoTeC i2 Pro CSV, MoTeC LDX timing beacons, MATLAB R2026a `.mat`, and interactive HTML.

### 4. 4-Wheel / Dual-Track Chassis Dynamics (`f1_sim/vehicle_dynamics.py`)
- **4-Corner Dynamic Normal Load Transfer**:
  Computes individual vertical tire loads ($F_{z,fl}, F_{z,fr}, F_{z,rl}, F_{z,rr}$) resolving:
  $$\Delta F_{\text{long}} = M_{\text{total}} \cdot a_x \cdot \frac{h_{\text{cg}}}{L}$$
  $$\Delta F_{\text{lat},f} = \frac{M_{\text{total}} a_y}{t_f} \left[ \frac{h_{\text{roll},f} b}{L} + \left(\frac{K_{\phi,f}}{K_{\phi,f} + K_{\phi,r}}\right) (h_{\text{cg}} - h_{\text{roll}}) \right]$$
  $$\Delta F_{\text{lat},r} = \frac{M_{\text{total}} a_y}{t_r} \left[ \frac{h_{\text{roll},r} a}{L} + \left(\frac{K_{\phi,r}}{K_{\phi,f} + K_{\phi,r}}\right) (h_{\text{cg}} - h_{\text{roll}}) \right]$$
- **Suspension Roll Stiffness Distribution**: Front and rear anti-roll bar (ARB) and spring wheel rates dictate axle roll stiffness ($K_{\phi,f}, K_{\phi,r}$), controlling mechanical understeer/oversteer balance.
- **Pacejka '02 Magic Formula Slip Model**: Combines load sensitivity $\mu(F_z)$ and thermal window $\mu(T_{\text{tire}})$ with lateral slip angles ($\alpha_f, \alpha_r$) and kinematic Ackermann steering angles ($\delta$).
- **Brake-by-Wire (BBW) Dynamic Migration**: Static baseline bias (56.5% front) dynamically migrates forward under heavy deceleration to maintain rear stability during 350 kW MGU-K regeneration.

### 5. 8-Speed Sequential Seamless-Shift Transmission (`f1_sim/transmission.py`)
- **FIA Homologated Gear Ratios**: 8 forward speeds ($1^{\text{st}}: 12.85$ to $8^{\text{th}}: 4.02$ overall ratio with final drive).
- **Engine RPM Dynamics**: Continuous rotational speed tracking ($4,000 - 12,100\text{ RPM}$) across Pirelli 18-inch wheels ($r_{\text{wheel}} = 0.360\text{ m}$).
- **15ms Seamless-Shift Torque Cuts**: 85% torque attenuation during shift transitions replicating hydraulic sequential actuators.

### 6. Official MoTeC i2 Pro & MATLAB R2026a Export
- **MoTeC CSV (`.csv`)**: 100 Hz calibrated telemetry with official header syntax (`Format,MoTeC CSV File`, `Sample Rate,100`) and engineering units (`km/h`, `kW`, `g`, `°C`, `N`, `deg`).
- **MoTeC LDX Beacons (`.ldx`)**: XML timing beacon markers for start/finish line and timing sectors 1, 2, and 3. Drag and drop directly into MoTeC i2 Pro!
- **Native MATLAB R2026a Suite (`matlab/`)**: Standalone MATLAB integrator (`f1_lts_simulation.m`), batch runner (`run_matlab_batch.m`), and `.mat` workspace importer.

---

## 🚀 Quickstart Guide

### 1. Launch the Ember Studio React Frontend (Recommended)

The simulator features a **Ember Studio** web application with editorial typography (*Playfair Display*, *Source Sans 3*, *Fira Code*), warm terracotta and amber palette, one-click pill controls, and decongested modular charts with separate legend boxes:

```bash
# Clone the repository
git clone https://github.com/krithikkrish/f1-laptime-simulator.git
cd f1-laptime-simulator

# Install Python backend dependencies
pip install -r requirements.txt

# Start the simulation API server (also serves the Ember Studio frontend)
python3 server.py 8000
```
Open **`http://localhost:8000`** in your browser!

For frontend development mode with Vite hot-reloading:
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 2. Alternative: Launch the Streamlit Workstation

```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

### 3. Command-Line Simulation Runner

Run simulations from terminal across any circuit:
```bash
# Run Spa-Francorchamps with MoTeC & MATLAB export
python3 run_simulation.py --track spa --setup balanced --export_motec --export_matlab

# Run Monaco Grand Prix with High-Downforce Monaco Spec
python3 run_simulation.py --track monaco --setup monaco --export_motec

# Run Monza with Monza Low-Drag Spec
python3 run_simulation.py --track monza --setup monza --export_motec
```

### 4. Run the Automated Test Suite

```bash
python3 -m unittest discover tests/
```
Runs 15 rigorous unit and integration tests covering:
- Static and dynamic 4-wheel vertical load conservation ($F_z = M g + F_{\text{downforce}}$).
- Pitch load transfer during braking and roll load transfer during cornering.
- Sequential transmission gear selection, RPM bounds, and shift cut torque attenuation.
- Homologated setup presets and parameter conversions.
- MoTeC CSV header syntax and LDX beacon XML structure.
- Full 0.01s Forward-Euler simulation convergence.
- 2025 FIA World Championship pole benchmark telemetry verification.

---

## 📁 Repository Structure

```
f1-laptime-simulator/
├── frontend/                   # Ember Studio Web App (React 19, Vite, Playfair Display & Source Sans 3)
│   ├── src/                    # App.jsx, index.css, modular components
│   └── dist/                   # Production build bundled for high-performance serving
├── server.py                   # High-performance Python REST API & Static Asset Server
├── app.py                      # McLaren ATLAS / MoTeC i2 Pro Dark Telemetry Workstation (Streamlit)
├── requirements.txt            # Python dependencies (numpy, scipy, matplotlib, pandas, streamlit, plotly, fastf1)
├── run_simulation.py           # CLI simulation runner with 24-track selector and export flags
├── optimize_lap.py             # SciPy SLSQP hybrid deployment trajectory optimizer
├── data_cache/                 # Automatic local disk cache for OpenF1 API sessions
├── tests/
│   └── test_f1_sim.py          # 15-test automated unit and integration suite
├── f1_sim/
│   ├── __init__.py             # Package API exports
│   ├── all_tracks.json         # Master 24-circuit 3D waypoints, elevation, weather & pole benchmarks
│   ├── tracks_data.py          # Calendar track factory and fuzzy circuit matching engine
│   ├── vehicle_dynamics.py     # 4-wheel dual-track chassis, pitch/roll load transfer, Pacejka, BBW
│   ├── transmission.py         # 8-speed sequential gearbox, engine RPM dynamics, 15ms shift cuts
│   ├── setup_sheet.py          # SetupSheet dataclass and FIA homologated presets (Monza, Monaco, etc.)
│   ├── motec_export.py         # MoTeC i2 Pro CSV exporter and LDX timing beacon generator
│   ├── lts_engine.py           # 0.01s Forward-Euler numerical integration engine
│   ├── interactive_plots.py    # Plotly multi-channel telemetry, A vs B delta traces, 3D track map
│   ├── openf1_client.py        # Real-world OpenF1 API client with retry backoff
│   ├── physics_weather.py      # CIPM-2007 humid air density, track temp grip & wind vector
│   ├── params.py               # 2026 technical regulations & vehicle dynamics parameters
│   ├── aero.py                 # Active aerodynamics (Z-Mode & X-Mode)
│   ├── powertrain.py           # 400kW ICE + 350kW MGU-K with 290-345 km/h taper
│   ├── tire_model.py           # Load-sensitive friction ellipse & thermal balance ODE
│   ├── track.py                # Periodic cubic spline track geometry & heading calculator
│   └── telemetry.py            # Matplotlib plotting routines
├── matlab/
│   ├── f1_lts_simulation.m     # High-precision 0.01s Forward-Euler engine in pure MATLAB
│   ├── import_f1_session.m     # Session & weather importer from .mat files
│   ├── plot_telemetry_interactive.m # Linked multi-channel interactive MATLAB figures
│   ├── run_matlab_batch.m      # Turnkey batch simulation and KPI report script
│   └── monza_session.mat       # Sample export session ready for immediate execution
└── output/                     # Generated telemetry plots, MoTeC CSVs, LDX beacons, and .mat files
```

---

## 📄 License
This project is licensed under the MIT License.
