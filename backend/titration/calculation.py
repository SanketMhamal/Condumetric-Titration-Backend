"""
Core calculation module — Fortran-to-Python port of conductometric titration analysis.

Implements:
- Dilution correction
- Strong acid splitting (min conductivity)
- Weak acid splitting (max diff-delta)
- Linear regression (MLSF)
- Equivalence point & angle calculation
"""

import math
import numpy as np
from scipy.stats import linregress


def apply_dilution(volumes, conductivities, v0):
    """
    Correct measured conductivities for dilution effect.
    Y_corrected = Y_measured * (V0 + v) / V0
    """
    volumes = np.asarray(volumes, dtype=np.float64)
    conductivities = np.asarray(conductivities, dtype=np.float64)
    return conductivities * (v0 + volumes) / v0


def split_strong(conductivities):
    """
    Strong acid: split at the index of minimum conductivity.
    Returns the index of the minimum value (0-based).
    """
    return int(np.argmin(conductivities))


def split_weak(conductivities):
    """
    Weak acid: split at the index where diff(delta) is maximised.

    delta_i    = |Y_i - Y_{i-1}|          (for i >= 1)
    diff_delta = |delta_i - delta_{i-1}|  (for i >= 2, i.e. from original index 3+)

    The split index (into the original array) is returned.
    Region A = [:split], Region B = [split:]
    """
    y = np.asarray(conductivities, dtype=np.float64)
    delta = np.abs(np.diff(y))                   # length n-1
    diff_delta = np.abs(np.diff(delta))           # length n-2

    # diff_delta[0] corresponds to original index 2, but Fortran starts
    # the search from index 4 (1-based), which is index 3 (0-based).
    # diff_delta index = original_index - 2
    # So search from diff_delta index 1 onward (original index 3).
    search_region = diff_delta[1:]                # skip first element
    max_idx_in_search = int(np.argmax(search_region))
    # Map back: diff_delta index = max_idx_in_search + 1,
    #           original index  = diff_delta_index + 2
    original_index = max_idx_in_search + 1 + 2    # = max_idx_in_search + 3
    return original_index


def _regression(x, y):
    """
    Perform least-squares linear regression.
    Returns dict with slope, intercept, r_squared, std_dev.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    result = linregress(x, y)
    slope = result.slope
    intercept = result.intercept
    r_value = result.rvalue
    r_squared = r_value ** 2

    # Standard deviation of residuals (matching Fortran: sqrt(sum(err^2) / n))
    predicted = slope * x + intercept
    residuals = y - predicted
    std_dev = float(np.sqrt(np.mean(residuals ** 2)))

    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "std_dev": std_dev,
    }


def find_equivalence(volumes, conductivities, acid_type, v0, apply_dilution_flag):
    """
    Full pipeline: correct → split → regress → intersect → angle.

    Parameters
    ----------
    volumes : list[float]
    conductivities : list[float]
    acid_type : str  ("strong" or "weak")
    v0 : float  (initial volume of acid solution)
    apply_dilution_flag : bool

    Returns
    -------
    dict  matching the API response specification
    """
    vols = np.asarray(volumes, dtype=np.float64)
    conds = np.asarray(conductivities, dtype=np.float64)

    # 1. Dilution correction
    if apply_dilution_flag:
        corrected = apply_dilution(vols, conds, v0)
    else:
        corrected = conds.copy()

    corrected_data = list(zip(vols.tolist(), corrected.tolist()))

    # 2. Split into two regions (ensure each has >= 2 points for regression)
    n = len(vols)
    if acid_type == "strong":
        split_idx = split_strong(corrected)
        # Region A = [:split_idx+1]  (split_idx+1 items)
        # Region B = [split_idx+1:]  (n - split_idx - 1 items)
        # Both need >= 2  =>  split_idx >= 1 and split_idx <= n-3
        split_idx = max(1, min(split_idx, n - 3))
        x_a = vols[: split_idx + 1]
        y_a = corrected[: split_idx + 1]
        x_b = vols[split_idx + 1:]
        y_b = corrected[split_idx + 1:]
    else:
        split_idx = split_weak(corrected)
        # Region A = [:split_idx]  (split_idx items)
        # Region B = [split_idx:]  (n - split_idx items)
        # Both need >= 2  =>  split_idx >= 2 and split_idx <= n-2
        split_idx = max(2, min(split_idx, n - 2))
        x_a = vols[:split_idx]
        y_a = corrected[:split_idx]
        x_b = vols[split_idx:]
        y_b = corrected[split_idx:]

    # 3. Linear regression on each region
    reg_a = _regression(x_a, y_a)
    reg_b = _regression(x_b, y_b)

    m1, c1 = reg_a["slope"], reg_a["intercept"]
    m2, c2 = reg_b["slope"], reg_b["intercept"]

    # 4. Intersection (equivalence point)
    x0 = (c1 - c2) / (m2 - m1)
    y0 = m1 * x0 + c1

    # 5. Angle between lines (dot product method)
    # Point A = intersection (equivalence point)
    # Point B = arbitrary point on Region A line (x = x0 - 1)
    # Point C = arbitrary point on Region B line (x = x0 + 1)
    xB = x0 - 1.0
    yB = m1 * xB + c1
    xC = x0 + 1.0
    yC = m2 * xC + c2

    # Vectors from A to B and A to C
    vec_AB = np.array([xB - x0, yB - y0])
    vec_AC = np.array([xC - x0, yC - y0])

    dot_product = np.dot(vec_AB, vec_AC)
    mag_AB = np.linalg.norm(vec_AB)
    mag_AC = np.linalg.norm(vec_AC)

    cos_alpha = np.clip(dot_product / (mag_AB * mag_AC), -1.0, 1.0)
    alpha_deg = math.degrees(math.acos(cos_alpha))

    # Helper to convert numpy types to native Python floats
    def _f(v):
        return float(v)

    return {
        "equivalence_point": {
            "volume": _f(round(x0, 5)),
            "conductivity": _f(round(y0, 5)),
        },
        "angle": _f(round(alpha_deg, 2)),
        "region_A": {
            "slope": _f(round(m1, 5)),
            "intercept": _f(round(c1, 5)),
            "r_squared": _f(round(reg_a["r_squared"], 5)),
        },
        "region_B": {
            "slope": _f(round(m2, 5)),
            "intercept": _f(round(c2, 5)),
            "r_squared": _f(round(reg_b["r_squared"], 5)),
        },
        "corrected_data": [[_f(v), _f(c)] for v, c in corrected_data],
    }
