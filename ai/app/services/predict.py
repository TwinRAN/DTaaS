import numpy as np
from typing import Any, Dict, List, Tuple


# --------- helpers (module-level, no nesting) ---------

def split_indices(names: List[str]) -> Tuple[List[int], List[int], List[int]]:
    """Return indices for history, noise, and other features."""
    hist_idx = [i for i, n in enumerate(names) if str(n).startswith("DL_hist_")]
    noise_idx = [i for i, n in enumerate(names) if str(n).startswith("noise_")]
    other_idx = [i for i in range(len(names)) if i not in set(hist_idx + noise_idx)]
    return hist_idx, noise_idx, other_idx


def order_hist_positions(feature_names: List[str], hist_idx: List[int]) -> List[int]:
    """Sort DL_hist_* indices by their trailing integer; fallback to given order."""
    if not hist_idx:
        return []
    hist_names = [feature_names[i] for i in hist_idx]
    try:
        order = sorted(range(len(hist_idx)), key=lambda k: int(str(hist_names[k]).split("_")[-1]))
        return [hist_idx[k] for k in order]
    except Exception:
        return hist_idx


def compute_window_base(hist_raw: List[float], mode: str) -> float:
    """Compute window scaling base with guards."""
    if mode == "window_mean":
        b = float(np.mean(hist_raw))
    elif mode == "window_anchor":
        b = float(hist_raw[-1])
    elif mode == "none":
        b = 1.0
    else:
        raise ValueError(f"Unknown window_scale_mode: {mode}")
    return max(b, 1e-8)


def scale_noise_abs_db(val_db: float, vmin: float, vmax: float) -> float:
    """Scale |dB| into [0,1] using fixed min/max (training rule)."""
    v = abs(float(val_db))
    return float(min(max((v - vmin) / (vmax - vmin), 0.0), 1.0))


# --------- main service ---------

def predict_with_model(model: Any, metadata: Dict[str, Any], features: Dict[str, float]) -> Dict[str, Any]:
    """
    Build the model input vector from a flat 'features' dict (keys must match training feature_names),
    apply training-time scaling (window + noise), predict on scaled target, and unscale to original units.

    Parameters
    ----------
    model : Any
        Fitted estimator (pickle-loaded).
    metadata : Dict[str, Any]
        Must include:
          - "feature_names" or "feature_names_in" (exact training order)
          - "window_size" (int)
          - scaling config either at metadata["scaling"] or top-level:
              {
                "window_scale_mode": "window_mean" | "window_anchor" | "none",
                "noise_scaling": {"min_abs_db": 50.0, "max_abs_db": 150.0}
              }
    features : Dict[str, float]
        Mapping of feature_name -> value (raw values in original units).
        - DL_hist_* are raw target history values (>0), oldest..newest inferred by suffix 0..W-1
        - noise_* are raw dB values to be min-max scaled on |dB|

    Returns
    -------
    dict:
        {
          "y_pred": float,          # unscaled prediction
          "y_pred_scaled": float,   # model-space prediction
          "base": float,            # window scaling base used
          "x_vector": list[float],  # exact vector fed to model
          "feature_names": list[str]
        }
    """
    # --- metadata essentials ---
    feature_names: List[str] = list(metadata.get("feature_names") or metadata.get("feature_names_in") or [])
    if not feature_names:
        raise ValueError("metadata.feature_names is required.")

    window_size = int(metadata.get("window_size", 0))
    if window_size <= 0:
        raise ValueError("metadata.window_size must be > 0.")

    # scaling config
    scaling = metadata.get("scaling") or {}
    window_scale_mode = scaling.get("window_scale_mode", metadata.get("window_scale_mode", "window_mean"))
    noise_cfg = scaling.get("noise_scaling", metadata.get("noise_scaling", {"min_abs_db": 50.0, "max_abs_db": 150.0}))
    vmin = float(noise_cfg.get("min_abs_db", 50.0))
    vmax = float(noise_cfg.get("max_abs_db", 150.0))
    if vmax <= vmin:
        raise ValueError("noise_scaling max_abs_db must be greater than min_abs_db.")

    # --- derive groups and sanity checks ---
    hist_idx, noise_idx, other_idx = split_indices(feature_names)
    if len(hist_idx) == 0:
        raise ValueError("Model metadata exposes no DL_hist_* features.")
    if len(hist_idx) != window_size:
        # tolerate metadata mismatch by trusting window_size
        # (we'll take the first window_size hist features in order)
        ordered_hist_positions = order_hist_positions(feature_names, hist_idx)[:window_size]
    else:
        ordered_hist_positions = order_hist_positions(feature_names, hist_idx)

    # --- collect raw history in order oldest..newest from provided features ---
    try:
        # names in ordered positions
        hist_names_ordered = [feature_names[i] for i in ordered_hist_positions]
        missing_hist = [n for n in hist_names_ordered if n not in features]
        if missing_hist:
            raise KeyError(f"Missing history features: {missing_hist}")
        hist_raw = [float(features[n]) for n in hist_names_ordered]
    except KeyError as ke:
        raise ValueError(str(ke)) from ke
    except Exception:
        raise ValueError("DL_hist_* values must be numeric.")

    if any(v <= 0.0 for v in hist_raw):
        raise ValueError("All DL_hist_* values must be > 0.")

    # --- compute base and scale history ---
    base = compute_window_base(hist_raw, window_scale_mode)
    hist_scaled = hist_raw if window_scale_mode == "none" else [v / base for v in hist_raw]

    # --- allocate input vector and fill ---
    x = [0.0] * len(feature_names)

    # history
    for pos, val in zip(ordered_hist_positions, hist_scaled):
        x[pos] = float(val)

    # noise (scale |dB|)
    if noise_idx:
        for pos in noise_idx:
            name = feature_names[pos]
            if name not in features:
                raise ValueError(f"Missing noise feature '{name}'.")
            x[pos] = scale_noise_abs_db(float(features[name]), vmin, vmax)

    # others: pass through as float (default 0.0 if absent)
    for pos in other_idx:
        name = feature_names[pos]
        if name in features:
            try:
                x[pos] = float(features[name])
            except Exception:
                raise ValueError(f"Feature '{name}' must be numeric.")

    # --- predict on scaled target, then unscale ---
    y_pred_scaled = float(model.predict([x])[0])
    y_pred = y_pred_scaled * base

    return {
        "y_pred": y_pred,
        "y_pred_scaled": y_pred_scaled,
        "base": base,
        "x_vector": x,
        "feature_names": feature_names,
    }
