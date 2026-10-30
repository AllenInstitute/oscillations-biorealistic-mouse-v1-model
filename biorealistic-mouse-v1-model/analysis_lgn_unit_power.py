#!/usr/bin/env python3
"""
Analysis script for LGN unit power spectra.

For each LGN unit, computes the power spectrum per trial and angle using
Welch's method, then saves summary statistics (mean, std, and SEM) of the
power across trials for each angle and unit to a CSV file.

The MUA and power are computed exactly as in
``analysis_memory_efficient_-2000.py`` (``ps_for_MUA_df``):

    counts  = np.histogram(spikes, bins=np.linspace(500, 3000, 1250))
    binsize = bins[1] - bins[0]
    mua     = counts / (binsize / 1e3)                          # Hz
    f, s    = scipy.signal.welch(mua, fs=1/binsize*1e3,
                                 nperseg=500, scaling="spectrum")
    s_norm  = s / np.sum(s)                                     # normalized power

The across-trial statistics are computed as in ``fig1C_dg_power.ipynb``:

    mean = np.mean(power, axis=0)
    std  = np.std(power,  axis=0)                # population std (ddof=0)
    se   = np.std(power,  axis=0) / np.sqrt(N)   # standard deviation of the mean

both for the raw power (``s``) and the normalized power (``s_norm``).

Data source:
    core/filternet_8dir_10trials/angle{angle}_trial{trial}/spikes.h5
    Each file contains:
        spikes/lgn/node_ids  -- integer unit IDs
        spikes/lgn/timestamps -- spike times in ms, range [0, 3000)

Output:
    core/metrics/lgn_unit_power/lgn_unit_power_spectrum.csv
    Columns: angle, node_id, f, n_trials,
             mean_power, std_power, sem_power,
             mean_power_norm, std_power_norm, sem_power_norm

Usage:
    python analysis_lgn_unit_power.py
    python analysis_lgn_unit_power.py --data_dir core/filternet_8dir_10trials \
        --output_dir core/metrics/lgn_unit_power
"""

import os
import sys
import time
import argparse
import gc

import numpy as np
import scipy.signal
import pandas as pd
import h5py

# ---------------------------------------------------------------------------
# Constants (match the conventions in analysis_memory_efficient_-2000.py)
# ---------------------------------------------------------------------------
ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]
N_TRIALS = 10

# Bins match ps_for_MUA_df / ps_for_MUA_df_layer exactly:
#   np.linspace(500, 3000, 1250) → 1249 bins, binsize ≈ 2.002 ms
BINS = np.linspace(500, 3000, 1250)
BINSIZE = BINS[1] - BINS[0]          # ms  (derived from bins, not hardcoded)
N_BINS = len(BINS) - 1                # 1249
FS = 1.0 / BINSIZE * 1e3             # Hz  (matches fs=1/binsize*1e3 in reference)

NPERSEG = 500                         # Welch segment length (samples)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_lgn_spikes(file_path: str):
    """Return (node_ids, timestamps) arrays from a spikes.h5 file."""
    with h5py.File(file_path, "r") as f:
        node_ids = f["spikes"]["lgn"]["node_ids"][:]
        timestamps = f["spikes"]["lgn"]["timestamps"][:]
    return node_ids, timestamps


def build_spike_rate_matrix(node_ids: np.ndarray,
                            timestamps: np.ndarray,
                            n_units: int) -> np.ndarray:
    """
    Build a (n_units × N_BINS) matrix of instantaneous firing rates (Hz).

    Uses np.histogram with the same bins as ps_for_MUA_df_layer so that
    binsize and fs are derived consistently:
        binsize = bins[1] - bins[0]
        mua     = counts / (binsize / 1e3)   # Hz
    """
    spike_matrix = np.zeros((n_units, N_BINS), dtype=np.float64)

    for uid in range(n_units):
        unit_mask = node_ids == uid
        spikes = timestamps[unit_mask]
        if len(spikes) == 0:
            continue
        counts, _ = np.histogram(spikes, bins=BINS)
        spike_matrix[uid] = counts / (BINSIZE / 1e3)   # counts → Hz

    return spike_matrix


def compute_power_spectra(spike_matrix: np.ndarray):
    """
    Compute Welch power spectrum for every unit simultaneously.

    Mirrors ps_for_MUA_df / ps_for_MUA_df_layer:
        f, s = scipy.signal.welch(mua, fs=1/binsize*1e3, nperseg=nperseg, scaling="spectrum")
        s_norm = s / np.sum(s)

    scipy.signal.welch operates along axis=-1, so passing a 2-D array
    (n_units × N_BINS) returns (f, power) where power has shape
    (n_units × n_freq).  FS is derived as 1/BINSIZE*1e3 from the histogram bins.

    The normalized power is computed per unit (each row sums to 1), matching
    ``s_norm = s / np.sum(s)`` in ps_for_MUA_df.  Units with no spikes (zero
    total power) yield an all-zero normalized spectrum instead of NaNs.
    """
    f, power = scipy.signal.welch(
        spike_matrix, fs=FS, nperseg=NPERSEG, scaling="spectrum" #, axis=-1
    )
    total = power.sum(axis=-1, keepdims=True)
    power_norm = np.divide(
        power, total, out=np.zeros_like(power), where=total > 0
    )
    return f, power, power_norm


def arr_to_str(arr: np.ndarray) -> str:
    """Serialize a 1-D numpy array to a string list for CSV storage."""
    return str(arr.tolist())


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_analysis(data_dir: str = "core/filternet_8dir_10trials",
                 output_dir: str = "core/metrics/lgn_unit_power") -> str:
    """
    Compute mean LGN unit power spectra across trials for each angle and
    save results to CSV.

    Returns the path of the output CSV file.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_csv = os.path.join(output_dir, "lgn_unit_power_spectrum.csv")

    print("=" * 60)
    print("LGN UNIT POWER SPECTRUM ANALYSIS")
    print("=" * 60)
    print(f"Data dir   : {data_dir}")
    print(f"Output CSV : {output_csv}")
    print(f"Window     : [{BINS[0]}, {BINS[-1]}] ms  |  bin = {BINSIZE:.4f} ms  |  {N_BINS} bins")
    print(f"Welch      : nperseg={NPERSEG}  fs={FS} Hz")
    print(f"Angles     : {ANGLES}")
    print(f"Trials     : {N_TRIALS}")

    # Determine n_units from the first available file
    first_file = os.path.join(data_dir, f"angle{ANGLES[0]}_trial0", "spikes.h5")
    if not os.path.exists(first_file):
        print(f"ERROR: First data file not found: {first_file}")
        sys.exit(1)

    with h5py.File(first_file, "r") as f:
        max_id = int(f["spikes"]["lgn"]["node_ids"][:].max())
    n_units = max_id + 1
    print(f"N units    : {n_units}")

    # Compute reference frequency axis
    dummy = np.zeros(N_BINS, dtype=np.float32)
    f_ref, _ = scipy.signal.welch(dummy, fs=FS, nperseg=NPERSEG, scaling="spectrum")
    n_freq = len(f_ref)
    f_ref_str = arr_to_str(f_ref)   # constant across all rows – pre-serialise once
    print(f"N freq bins: {n_freq}  (0–{f_ref.max():.1f} Hz)")
    print("=" * 60)

    header_written = False
    start_time = time.time()
    total_rows = 0

    for angle_idx, angle in enumerate(ANGLES):
        t_angle = time.time()
        print(f"\nAngle {angle:>3}°  ({angle_idx + 1}/{len(ANGLES)})")

        # Streaming sums of the raw power (s) and normalized power (s_norm)
        # so we never hold all trials in memory at once.
        power_sum = np.zeros((n_units, n_freq), dtype=np.float64)
        power_sq_sum = np.zeros((n_units, n_freq), dtype=np.float64)
        norm_sum = np.zeros((n_units, n_freq), dtype=np.float64)
        norm_sq_sum = np.zeros((n_units, n_freq), dtype=np.float64)
        valid_trials = 0

        for trial in range(N_TRIALS):
            file_path = os.path.join(data_dir, f"angle{angle}_trial{trial}", "spikes.h5")
            if not os.path.exists(file_path):
                print(f"  trial {trial}: NOT FOUND – {file_path}")
                continue

            try:
                node_ids, timestamps = load_lgn_spikes(file_path)
                spike_matrix = build_spike_rate_matrix(node_ids, timestamps, n_units)
                _, power, power_norm = compute_power_spectra(spike_matrix)

                power_sum += power
                power_sq_sum += power ** 2
                norm_sum += power_norm
                norm_sq_sum += power_norm ** 2
                valid_trials += 1

                del node_ids, timestamps, spike_matrix, power, power_norm
                gc.collect()
                print(f"  trial {trial}: OK")

            except Exception as exc:
                print(f"  trial {trial}: ERROR – {str(exc)[:120]}")

        if valid_trials == 0:
            print(f"  No valid trials – skipping angle {angle}.")
            continue

        # Across-trial statistics, matching fig1C_dg_power.ipynb:
        #   mean = np.mean(power, axis=0)
        #   std  = np.std(power,  axis=0)               # population std (ddof=0)
        #   se   = np.std(power,  axis=0) / np.sqrt(N)  # std of the mean
        # The population std is computed in a streaming, Bessel-free way as
        #   std = sqrt(max(E[X²] − (E[X])², 0)).
        sqrt_n = np.sqrt(valid_trials)

        mean_power = power_sum / valid_trials
        std_power = np.sqrt(np.maximum(power_sq_sum / valid_trials - mean_power ** 2, 0.0))
        sem_power = std_power / sqrt_n

        mean_power_norm = norm_sum / valid_trials
        std_power_norm = np.sqrt(np.maximum(norm_sq_sum / valid_trials - mean_power_norm ** 2, 0.0))
        sem_power_norm = std_power_norm / sqrt_n

        # Build DataFrame (one row per unit)
        angle_df = pd.DataFrame({
            "angle": angle,
            "node_id": np.arange(n_units),
            "f": f_ref_str,                                   # same for every row
            "n_trials": valid_trials,
            "mean_power": [arr_to_str(mean_power[uid]) for uid in range(n_units)],
            "std_power":  [arr_to_str(std_power[uid])  for uid in range(n_units)],
            "sem_power":  [arr_to_str(sem_power[uid])  for uid in range(n_units)],
            "mean_power_norm": [arr_to_str(mean_power_norm[uid]) for uid in range(n_units)],
            "std_power_norm":  [arr_to_str(std_power_norm[uid])  for uid in range(n_units)],
            "sem_power_norm":  [arr_to_str(sem_power_norm[uid])  for uid in range(n_units)],
        })

        if not header_written:
            angle_df.to_csv(output_csv, index=False, mode="w")
            header_written = True
        else:
            angle_df.to_csv(output_csv, index=False, mode="a", header=False)

        total_rows += len(angle_df)
        elapsed_angle = time.time() - t_angle
        print(f"  Saved {len(angle_df):,} rows  |  angle took {elapsed_angle:.1f} s")

        del power_sum, power_sq_sum, norm_sum, norm_sq_sum
        del mean_power, std_power, sem_power
        del mean_power_norm, std_power_norm, sem_power_norm
        del angle_df
        gc.collect()

    # Summary
    elapsed_total = time.time() - start_time
    print(f"\n{'=' * 60}")
    print("ANALYSIS COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total time  : {elapsed_total / 60:.1f} min")
    print(f"Total rows  : {total_rows:,}")
    if os.path.exists(output_csv):
        size_mb = os.path.getsize(output_csv) / (1024 ** 2)
        print(f"Output file : {output_csv}  ({size_mb:.1f} MB)")
    print("=" * 60)

    return output_csv


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Compute Welch power spectra for individual LGN units "
            "per trial/angle, then average across trials."
        )
    )
    parser.add_argument(
        "--data_dir",
        default="core/filternet_8dir_10trials",
        help=(
            "Root directory that contains angle{A}_trial{T}/ subdirectories "
            "with spikes.h5 files.  (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--output_dir",
        default="core/metrics/lgn_unit_power",
        help="Directory where the output CSV will be saved.  (default: %(default)s)",
    )
    args = parser.parse_args()
    run_analysis(data_dir=args.data_dir, output_dir=args.output_dir)
