"""
Track representation and real-world circuit geometry engine.
Computes arc length, curvature kappa(s), corner radius R(s), elevation profile,
and grade angle theta(s) using periodic cubic spline interpolation.
Includes accurate models for Monza and Silverstone.
"""

from dataclasses import dataclass
import numpy as np
from scipy.interpolate import CubicSpline


@dataclass
class Track:
    name: str
    length: float                      # Total track length (meters)
    s: np.ndarray                      # Cumulative distance along track (m)
    x: np.ndarray                      # Easting / X coordinates (m)
    y: np.ndarray                      # Northing / Y coordinates (m)
    z: np.ndarray                      # Elevation / Z coordinates (m)
    curvature: np.ndarray              # Signed curvature kappa (1/m)
    corner_radius: np.ndarray          # Corner radius R(s) = 1 / max(|kappa|, 1e-5) (m)
    grade: np.ndarray                  # Track grade sin(theta) = dz/ds (dimensionless)
    is_corner: np.ndarray              # Boolean mask for corner zones
    sectors: list                      # [(name, s_start, s_end), ...]
    heading: np.ndarray = None         # Tangent heading angle (radians, -pi to pi)

    def interpolate(self, s_query: float):
        """Query track state at any arbitrary arc-length s."""
        s_norm = s_query % self.length
        idx = np.searchsorted(self.s, s_norm, side="right") - 1
        idx = np.clip(idx, 0, len(self.s) - 2)
        ratio = (s_norm - self.s[idx]) / (self.s[idx + 1] - self.s[idx] + 1e-9)
        
        curv = (1 - ratio) * self.curvature[idx] + ratio * self.curvature[idx + 1]
        radius = (1 - ratio) * self.corner_radius[idx] + ratio * self.corner_radius[idx + 1]
        gr = (1 - ratio) * self.grade[idx] + ratio * self.grade[idx + 1]
        x_pt = (1 - ratio) * self.x[idx] + ratio * self.x[idx + 1]
        y_pt = (1 - ratio) * self.y[idx] + ratio * self.y[idx + 1]
        hdg = (1 - ratio) * self.heading[idx] + ratio * self.heading[idx + 1] if self.heading is not None else 0.0
        
        return {
            "s": s_norm,
            "x": x_pt,
            "y": y_pt,
            "heading": hdg,
            "curvature": curv,
            "corner_radius": radius,
            "grade": gr,
            "is_corner": abs(curv) > 0.0025,
        }


def build_track_from_waypoints(name: str, x_pts: np.ndarray, y_pts: np.ndarray, z_pts: np.ndarray = None, ds: float = 1.0) -> Track:
    """
    Constructs a smooth, closed Track object from discrete 2D/3D waypoints using periodic splines.
    """
    x_pts = np.array(x_pts, dtype=float)
    y_pts = np.array(y_pts, dtype=float)
    if z_pts is None:
        z_pts = np.zeros_like(x_pts)
    else:
        z_pts = np.array(z_pts, dtype=float)

    # Filter out duplicate or near-identical adjacent waypoints
    dists = np.sqrt(np.diff(x_pts)**2 + np.diff(y_pts)**2 + np.diff(z_pts)**2)
    keep = np.concatenate(([True], dists > 0.5))
    x_pts, y_pts, z_pts = x_pts[keep], y_pts[keep], z_pts[keep]

    # Normalize closing point to ensure exact periodicity for CubicSpline
    if np.hypot(x_pts[-1] - x_pts[0], y_pts[-1] - y_pts[0]) > 2.0:
        x_pts = np.append(x_pts, x_pts[0])
        y_pts = np.append(y_pts, y_pts[0])
        z_pts = np.append(z_pts, z_pts[0])
    else:
        x_pts[-1] = x_pts[0]
        y_pts[-1] = y_pts[0]
        z_pts[-1] = z_pts[0]


    # Calculate chord lengths
    dx = np.diff(x_pts)
    dy = np.diff(y_pts)
    dz = np.diff(dz_pts := z_pts)
    seg_lens = np.sqrt(dx**2 + dy**2 + dz**2)
    s_raw = np.concatenate(([0.0], np.cumsum(seg_lens)))
    total_len = s_raw[-1]

    # Periodic cubic spline fits
    cs_x = CubicSpline(s_raw, x_pts, bc_type='periodic')
    cs_y = CubicSpline(s_raw, y_pts, bc_type='periodic')
    cs_z = CubicSpline(s_raw, z_pts, bc_type='periodic')

    # Uniform spatial sampling
    num_pts = int(np.ceil(total_len / ds))
    s_grid = np.linspace(0.0, total_len, num_pts, endpoint=False)

    x_grid = cs_x(s_grid)
    y_grid = cs_y(s_grid)
    z_grid = cs_z(s_grid)

    # First and second derivatives w.r.t distance s
    dx_ds = cs_x(s_grid, 1)
    dy_ds = cs_y(s_grid, 1)
    d2x_ds2 = cs_x(s_grid, 2)
    d2y_ds2 = cs_y(s_grid, 2)
    dz_ds = cs_z(s_grid, 1)

    # Curvature formula: kappa = (x' y'' - y' x'') / (x'^2 + y'^2)^(3/2)
    speed_sq = dx_ds**2 + dy_ds**2
    raw_curvature = (dx_ds * d2y_ds2 - dy_ds * d2x_ds2) / np.maximum(speed_sq**1.5, 1e-9)

    # Smooth raw curvature across discrete spline chord points using a 15m rolling Gaussian window
    kernel_size = max(5, int(15.0 / ds))
    if kernel_size % 2 == 0:
        kernel_size += 1
    gaussian_kernel = np.exp(-0.5 * (np.linspace(-2, 2, kernel_size))**2)
    gaussian_kernel /= np.sum(gaussian_kernel)
    curvature = np.convolve(np.pad(raw_curvature, kernel_size // 2, mode='wrap'), gaussian_kernel, mode='valid')

    # Corner radius R(s) with realistic F1 racing line floor (R_min >= 28m for tightest chicanes)
    abs_curv = np.abs(curvature)
    corner_radius = np.where(abs_curv > 1e-4, np.maximum(28.0, 1.0 / abs_curv), 10_000.0)

    # Grade sin(theta) = dz/ds / sqrt(dx^2 + dy^2 + dz^2)
    grade = dz_ds / np.maximum(np.sqrt(speed_sq + dz_ds**2), 1e-9)

    is_corner = abs_curv > 0.0025  # R < 400m considered corner

    # Tangent heading angle (radians) along circuit path
    heading = np.arctan2(dy_ds, dx_ds)

    # Default 3 F1 Sectors (roughly 33% each)
    s_max = s_grid[-1]
    sectors = [
        ("Sector 1", 0.0, s_max * 0.33),
        ("Sector 2", s_max * 0.33, s_max * 0.68),
        ("Sector 3", s_max * 0.68, s_max),
    ]

    return Track(
        name=name,
        length=total_len,
        s=s_grid,
        x=x_grid,
        y=y_grid,
        z=z_grid,
        curvature=curvature,
        corner_radius=corner_radius,
        grade=grade,
        is_corner=is_corner,
        sectors=sectors,
        heading=heading,
    )


from .tracks_data import MONZA_X, MONZA_Y, SILVERSTONE_X, SILVERSTONE_Y


def create_monza_track(ds: float = 1.0) -> Track:
    """
    Official Autodromo Nazionale Monza circuit (5,793m) from real FIA/OpenStreetMap GPS coordinates.
    Exact geographical layout, orientation, and corner geometry:
    - Rettifilo Tribune (Main Straight)
    - Variante del Rettifilo (Turns 1-2 Chicane)
    - Curva Biassono / Curva Grande (Turn 3)
    - Variante della Roggia (Turns 4-5 Chicane)
    - Curva di Lesmo 1 & 2 (Turns 6-7)
    - Curva del Serraglio
    - Variante Ascari (Turns 8-9-10 Chicane)
    - Rettifilo Posteriore (Back Straight)
    - Curva Parabolica / Curva Alboreto (Turn 11)
    """
    x_raw = np.array(MONZA_X)
    y_raw = np.array(MONZA_Y)
    z_raw = np.zeros_like(x_raw)

    track = build_track_from_waypoints("Autodromo Nazionale Monza", x_raw, y_raw, z_raw, ds=ds)
    # Scale total length precisely to official 5,793.0 m
    scale = 5793.0 / track.length
    x_scaled = x_raw * scale
    y_scaled = y_raw * scale
    z_scaled = z_raw * scale

    track_final = build_track_from_waypoints("Autodromo Nazionale Monza", x_scaled, y_scaled, z_scaled, ds=ds)
    
    # Official Monza F1 Timing Sectors
    track_final.sectors = [
        ("Sector 1 (Start - Curva Grande)", 0.0, 1620.0),
        ("Sector 2 (Roggia - Lesmo - Serraglio)", 1620.0, 3850.0),
        ("Sector 3 (Ascari - Parabolica - Finish)", 3850.0, track_final.length),
    ]
    return track_final


def create_silverstone_track(ds: float = 1.0) -> Track:
    """
    Official Silverstone Grand Prix Circuit (5,891m) from real FIA/OpenStreetMap GPS coordinates.
    Exact geographical layout and high-speed flow:
    - Hamilton Straight (Start / Finish)
    - Abbey (Turn 1) & Farm Curve (Turn 2)
    - Arena Complex: Village (Turn 3) & The Loop (Turn 4)
    - Aintree (Turn 5) & Wellington Straight
    - Brooklands (Turn 6) & Luffield (Turn 7)
    - Woodcote (Turn 8)
    - Copse (Turn 9)
    - Maggotts, Becketts & Chapel Complex (Turns 10-14)
    - Hangar Straight
    - Stowe (Turn 15)
    - Vale (Turn 16) & Club (Turns 17-18)
    """
    x_raw = np.array(SILVERSTONE_X)
    y_raw = np.array(SILVERSTONE_Y)
    z_raw = np.zeros_like(x_raw)

    track = build_track_from_waypoints("Silverstone Grand Prix Circuit", x_raw, y_raw, z_raw, ds=ds)
    scale = 5891.0 / track.length
    x_scaled = x_raw * scale
    y_scaled = y_raw * scale
    z_scaled = z_raw * scale

    track_final = build_track_from_waypoints("Silverstone Grand Prix Circuit", x_scaled, y_scaled, z_scaled, ds=ds)

    # Official Silverstone F1 Timing Sectors
    track_final.sectors = [
        ("Sector 1 (Hamilton - Abbey - Arena)", 0.0, 1720.0),
        ("Sector 2 (Wellington - Copse - Becketts)", 1720.0, 3950.0),
        ("Sector 3 (Hangar - Stowe - Vale - Club)", 3950.0, track_final.length),
    ]
    return track_final
