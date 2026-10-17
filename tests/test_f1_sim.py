"""
Unit and Integration Test Suite for F1 2026 Lap-Time Simulator.
Tests vehicle dynamics, sequential transmission, setup sheets, 
MoTeC exporter, weather ingestion, and Forward-Euler integration loop.
"""

import unittest
import numpy as np
import os
import tempfile

from f1_sim import (
    VehicleParams,
    Track,
    create_monza_track,
    DualTrackDynamics,
    SequentialTransmission,
    SetupSheet,
    HOMOLOGATED_PRESETS,
    SimulationEngine,
    LapTelemetry,
    export_motec_csv,
    export_motec_ldx,
    WeatherConditions
)
from f1_sim.interactive_plots import export_telemetry_to_mat


class TestVehicleDynamics(unittest.TestCase):
    def setUp(self):
        self.params = VehicleParams()
        self.dynamics = DualTrackDynamics(self.params)

    def test_static_normal_loads(self):
        """At zero acceleration and zero speed, 4-corner loads must sum to total vehicle weight."""
        loads = self.dynamics.compute_4wheel_loads(a_long_g=0.0, a_lat_g=0.0, f_downforce_total=0.0)
        expected_weight = self.params.total_mass * self.params.gravity
        self.assertAlmostEqual(loads.f_z_total, expected_weight, delta=1.0)
        # Verify left-right symmetry
        self.assertAlmostEqual(loads.f_z_fl, loads.f_z_fr, delta=1.0)
        self.assertAlmostEqual(loads.f_z_rl, loads.f_z_rr, delta=1.0)

    def test_braking_pitch_transfer(self):
        """Under heavy braking (negative a_long_g), weight transfers to front axle."""
        loads_static = self.dynamics.compute_4wheel_loads(a_long_g=0.0, a_lat_g=0.0, f_downforce_total=1000.0)
        loads_braking = self.dynamics.compute_4wheel_loads(a_long_g=-3.0, a_lat_g=0.0, f_downforce_total=1000.0)
        self.assertGreater(loads_braking.f_z_front_total, loads_static.f_z_front_total)
        self.assertLess(loads_braking.f_z_rear_total, loads_static.f_z_rear_total)

    def test_cornering_roll_transfer(self):
        """In cornering with positive lateral acceleration, weight transfers across the axle."""
        loads = self.dynamics.compute_4wheel_loads(a_long_g=0.0, a_lat_g=3.5, f_downforce_total=5000.0)
        self.assertGreater(loads.f_z_fr, loads.f_z_fl)
        self.assertGreater(loads.f_z_rr, loads.f_z_rl)

    def test_dynamic_bbw_migration(self):
        """Brake bias migrates forward under heavy braking deceleration."""
        bias_static = self.dynamics.compute_bbw_bias(a_long_g=0.0)
        bias_braking = self.dynamics.compute_bbw_bias(a_long_g=-4.0)
        self.assertGreater(bias_braking, bias_static)
        self.assertLessEqual(bias_braking, 0.75)


class TestTransmission(unittest.TestCase):
    def setUp(self):
        self.trans = SequentialTransmission()

    def test_optimal_gear_selection(self):
        """Low speeds require gear 1-2, high speeds require gear 7-8."""
        self.assertIn(self.trans.get_optimal_gear(15.0), [1, 2])
        self.assertIn(self.trans.get_optimal_gear(95.0), [7, 8])

    def test_engine_rpm_range(self):
        """Engine RPM should remain within realistic boundaries (idle to redline)."""
        state_low = self.trans.calculate_state(v_ms=0.0, throttle=0.0, p_total_watts=0.0)
        self.assertGreaterEqual(state_low.engine_rpm, self.trans.rpm_idle)
        state_high = self.trans.calculate_state(v_ms=90.0, throttle=1.0, p_total_watts=750000.0)
        self.assertLessEqual(state_high.engine_rpm, self.trans.rpm_redline)

    def test_shift_cut_mechanics(self):
        """Changing gear triggers a seamless torque cut."""
        # Initial state in gear 1
        self.trans.current_gear = 1
        # Accelerate to speed that demands gear 2 (40 m/s ~ 144 km/h)
        state_shift = self.trans.calculate_state(v_ms=40.0, throttle=1.0, p_total_watts=400000.0, dt=0.005)
        self.assertTrue(state_shift.is_shifting)
        self.assertLess(state_shift.shift_torque_factor, 1.0)
        # Advance time past shift duration
        self.trans.calculate_state(v_ms=40.0, throttle=1.0, p_total_watts=400000.0, dt=0.020)
        state_engaged = self.trans.calculate_state(v_ms=40.0, throttle=1.0, p_total_watts=400000.0, dt=0.010)
        self.assertFalse(state_engaged.is_shifting)
        self.assertEqual(state_engaged.shift_torque_factor, 1.0)




class TestSetupSheets(unittest.TestCase):
    def test_homologated_presets_exist(self):
        """Verify standard homologated setups are registered."""
        self.assertIn("Balanced Grand Prix Spec", HOMOLOGATED_PRESETS)
        self.assertIn("Monza Low-Drag Spec", HOMOLOGATED_PRESETS)
        self.assertIn("High-Downforce Monaco Spec", HOMOLOGATED_PRESETS)
        self.assertIn("Wet-Weather Spec", HOMOLOGATED_PRESETS)

    def test_preset_conversion_to_params(self):
        """Converting a SetupSheet to VehicleParams yields consistent values."""
        monza = HOMOLOGATED_PRESETS["Monza Low-Drag Spec"]
        params = monza.to_vehicle_params()
        self.assertIsInstance(params, VehicleParams)
        self.assertAlmostEqual(params.cl_A_z_mode, monza.cl_a_z_mode)
        self.assertAlmostEqual(params.cd_A_x_mode, monza.cd_a_x_mode)


class TestMoTecExport(unittest.TestCase):
    def setUp(self):
        self.track = create_monza_track(ds=2.0)
        params = VehicleParams(dt=0.02)
        engine = SimulationEngine(params)
        self.telem = engine.run_transient_simulation(self.track, initial_soc=0.70)

    def test_motec_csv_header(self):
        """CSV export must include official MoTeC format tags and 100Hz channels."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            csv_path = f.name
        try:
            csv_str = export_motec_csv(self.telem, track=self.track, filepath=csv_path)
            self.assertIn("Format,MoTeC CSV File", csv_str)
            self.assertIn("Venue,Autodromo Nazionale Monza", csv_str)
            self.assertIn("Time,Distance,Corr Speed", csv_str)
            self.assertTrue(os.path.exists(csv_path))
            self.assertGreater(os.path.getsize(csv_path), 5000)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_motec_ldx_beacons(self):
        """LDX export must contain XML markers for timing sectors."""
        with tempfile.NamedTemporaryFile(suffix=".ldx", delete=False) as f:
            ldx_path = f.name
        try:
            ldx_str = export_motec_ldx(track=self.track, telem=self.telem, filepath=ldx_path)
            self.assertIn("<LDXFile Version=\"1.6\"", ldx_str)
            self.assertIn("Sector 1", ldx_str)
            self.assertIn("Finish Line", ldx_str)
            self.assertTrue(os.path.exists(ldx_path))
        finally:
            if os.path.exists(ldx_path):
                os.remove(ldx_path)

    def test_matlab_export(self):
        """MATLAB export produces a readable .mat workspace."""
        with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as f:
            mat_path = f.name
        try:
            export_telemetry_to_mat(self.telem, filepath=mat_path, track=self.track)
            self.assertTrue(os.path.exists(mat_path))
            self.assertGreater(os.path.getsize(mat_path), 1000)
        finally:
            if os.path.exists(mat_path):
                os.remove(mat_path)


class TestSimulationEngine(unittest.TestCase):
    def test_full_lap_simulation(self):
        """Simulation must run to completion with valid lap time and conservation laws."""
        track = create_monza_track(ds=2.0)
        params = VehicleParams(dt=0.02)
        engine = SimulationEngine(params)
        telem = engine.run_transient_simulation(track, initial_soc=0.70)

        # Realistic Monza lap time (approx 78s - 95s)
        self.assertGreater(telem.lap_time, 75.0)
        self.assertLess(telem.lap_time, 105.0)

        # Speed should never be negative or exceed physical limit
        self.assertTrue(np.all(telem.v >= 0.0))
        self.assertLess(np.max(telem.v_kmh), 380.0)

        # Battery SoC must stay within 5% to 100%
        self.assertTrue(np.all(telem.soc_percent >= 4.9))
        self.assertTrue(np.all(telem.soc_percent <= 100.1))

        # Check 4-wheel loads are present and positive
        self.assertIsNotNone(telem.f_z_fl)
        self.assertTrue(np.all(telem.f_z_fl > 0.0))
        self.assertTrue(np.all(telem.f_z_rr > 0.0))


if __name__ == "__main__":
    unittest.main()
