#!/usr/bin/env python3
"""
Memory-efficient analysis script for drifting gratings.
Processes data in chunks to avoid memory issues.
"""

import os
import sys
import time
import numpy as np
import scipy.signal
import pandas as pd
from io import StringIO
import argparse
import gc
import pickle

# Set pandas options to prevent array truncation
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

# Import required modules
try:
    from importlib import reload
    import plotting_utils

    reload(plotting_utils)
    from plotting_utils import data_organize

    print("✓ Successfully imported data_organize")
except ImportError as e:
    print(f"✗ Failed to import plotting_utils: {e}")
    sys.exit(1)

# Constants
DRIFTING_ANGLES = [
    "theta0",
    "theta45",
    "theta90",
    "theta135",
    "theta180",
    "theta225",
    "theta270",
    "theta315",
]

# Perturbation conditions mapping
PERTURB_DICT = {
    "L4": "_opto_layer_silencing_L1_L23_L5_L6_-2000",
    "silencing all i4Pvalb": "_onlyL4_-2000_silencing_i4Pvalb_100perc",
    "silencing all i4Sst": "_onlyL4_-2000_silencing_i4Sst_100perc",
    "silencing all i4Vip": "_onlyL4_-2000_silencing_i4Vip_100perc",
    "silencing 0.8333 i4Pvalb": "_onlyL4_-2000_silencing_i4Pvalb_83.33perc",
    "silencing 0.8333 i4Sst": "_onlyL4_-2000_silencing_i4Sst_83.33perc",
    "silencing 0.8333 i4Vip": "_onlyL4_-2000_silencing_i4Vip_83.33perc",
    "silencing 0.75 i4Pvalb": "_onlyL4_-2000_silencing_i4Pvalb_75.0perc",
    "silencing 0.75 i4Sst": "_onlyL4_-2000_silencing_i4Sst_75.0perc",
    "silencing 0.75 i4Vip": "_onlyL4_-2000_silencing_i4Vip_75.0perc",
    "silencing 0.625 i4Pvalb": "_onlyL4_-2000_silencing_i4Pvalb_62.5perc",
    "silencing 0.625 i4Sst": "_onlyL4_-2000_silencing_i4Sst_62.5perc",
    "silencing 0.625 i4Vip": "_onlyL4_-2000_silencing_i4Vip_62.5perc",
    "silencing 0.5 i4Pvalb": "_onlyL4_-2000_silencing_i4Pvalb_50perc",
    "silencing 0.5 i4Sst": "_onlyL4_-2000_silencing_i4Sst_50perc",
    "silencing 0.5 i4Vip": "_onlyL4_-2000_silencing_i4Vip_50perc",
    "silencing 0.25 i4Pvalb": "_onlyL4_-2000_silencing_i4Pvalb_25perc",
    "silencing 0.25 i4Sst": "_onlyL4_-2000_silencing_i4Sst_25perc",
    "silencing 0.25 i4Vip": "_onlyL4_-2000_silencing_i4Vip_25perc",
    "silencing 0.1 i4Pvalb": "_onlyL4_-2000_silencing_i4Pvalb_10perc",
    "silencing 0.1 i4Sst": "_onlyL4_-2000_silencing_i4Sst_10perc",
    "silencing 0.1 i4Vip": "_onlyL4_-2000_silencing_i4Vip_10perc",
}


def get_config_range(drifting_angle):
    """Get trial range and offset for angle."""
    angle_map = {
        "theta0": (range(0, 10), 0),
        "theta45": (range(10, 20), 10),
        "theta90": (range(20, 30), 20),
        "theta135": (range(30, 40), 30),
        "theta180": (range(40, 50), 40),
        "theta225": (range(50, 60), 50),
        "theta270": (range(60, 70), 60),
        "theta315": (range(70, 80), 70),
    }
    return angle_map.get(drifting_angle, (range(0, 10), 0))


def build_file_path(net_name, network_option, condition, trial):
    """Build configuration file path."""
    base_name = "8dir_10trials"

    if condition != "no perturb":
        condition_suffix = PERTURB_DICT[condition]
        dir_name = f"{base_name}{condition_suffix}_{network_option}"
    else:
        dir_name = f"{base_name}_{network_option}"

    full_path = os.path.join(net_name, "configs", dir_name)
    return f"{full_path}/config_{trial}.json"


def ps_for_MUA_df(row, bins=np.linspace(500, 3000, 1250), nperseg=500):
    # power spectral analysis for population activity using welch's method
    # INPUTS:
    # row: a row of the dataframe
    # stim_freq: frequency of interest, same as the stimulus frequency e.g. 40Hz
    # bins: bins for population activity, default is 5 ms
    # nperseg: nperseg for welch method, default is 100*5ms = 500ms
    # OUTPUTS:
    # f: frequency
    # s: power spectrum during stimulus presentation
    # s_stim: power spectrum at stimulus frequency
    # s_norm: normalized power spectrum during stimulus presentation
    # s_stim_norm: normalized power spectrum at stimulus frequency
    spikes = row["timestamps"]
    # n_neuron = row["n_neuron"]
    (counts, bins) = np.histogram(spikes, bins=bins)
    binsize = bins[1] - bins[0]
    mua = counts / (
        binsize / 1e3
    )  # Hz - normalized by thr total number of neurons n_neuron *
    f, s = scipy.signal.welch(
        mua, fs=1 / binsize * 1e3, nperseg=nperseg, scaling="spectrum"
    )
    s_norm = s / np.sum(s)

    return f, mua, s, s_norm

def ps_for_MUA_df_layer(row, bins=np.linspace(500, 3000, 1250), nperseg=500):
    """Power spectral analysis for layer-grouped MUA data."""
    spikes = row["timestamps"]
    # Flatten all spike times from all cells in this layer/condition/trial/dir
    all_spikes = []
    for spike_list in spikes:
        if isinstance(spike_list, (list, np.ndarray)):
            all_spikes.extend(spike_list)
    
    if len(all_spikes) == 0:
        # Return empty arrays if no spikes
        return np.array([]), np.array([]), np.array([])
    
    (counts, bins) = np.histogram(all_spikes, bins=bins)
    binsize = bins[1] - bins[0]
    mua = counts / (binsize / 1e3)  # Hz
    
    f, s = scipy.signal.welch(
        mua, fs=1 / binsize * 1e3, nperseg=nperseg, scaling="spectrum"
    )
    return f, s, mua


def process_single_trial_grouped(
    net_name, network_option, condition, trial, num_trials, angle
):
    """Process single trial and return grouped data directly to save memory."""

    try:
        file_path = build_file_path(net_name, network_option, condition, trial)

        if not os.path.exists(file_path):
            return None

        # Suppress verbose output from data_organize
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            _, spike_df = data_organize(file_path, t_min=500, t_max=3000)
        finally:
            sys.stdout = old_stdout

        if spike_df is None or spike_df.empty:
            return None

        # Add metadata
        spike_df = spike_df.assign(
            condition=condition,
            trial=trial - num_trials,
            dir=angle,
            perc=PERTURB_DICT[condition].split("_")[-1].split("perc")[0] if condition != "no perturb" else "0",
            cell_layer=spike_df["layer"] + " " + spike_df["cell_type"],
        )

        #
        spike_df[["layer", "cell"]] = spike_df.apply(
            lambda x: x["cell_layer"].split(" "), axis=1, result_type="expand"
        )

        # # Group by neuron immediately to reduce memory usage
        # spike_neuron_df = (
        #     spike_df.groupby(["condition", "trial", "cell_layer", "node_ids", "dir"], sort=False)
        #     ["timestamps"].agg(list).reset_index()
        # )

        # Group by cell type and get multi-unit activity
        mua_power_df = (
            spike_df.groupby(
                ["condition", "trial", "layer", "cell", "dir"], sort=False
            )["timestamps"]
            .agg(list)
            .to_frame()
            .reset_index()
        )

        # Calculate the power spectrum
        mua_power_df[["f", "mua", "power", "power_norm"]] = mua_power_df.apply(
            ps_for_MUA_df,
            # bins=bins,
            # nperseg=nperseg,
            axis=1,
            result_type="expand",
        )

        # Clean up original dataframe
        del spike_df
        gc.collect()

        return mua_power_df

    except Exception as e:
        print(
            f"Error processing {condition}, trial {trial}, angle {angle}: {str(e)[:100]}"
        )
        return None


def run_analysis_memory_efficient(
    net_name="core", network_option="checkpoint", angles=None, conditions=None
):
    """Run the analysis with memory efficiency."""

    if angles is None:
        angles = DRIFTING_ANGLES
    if conditions is None:
        conditions = list(PERTURB_DICT.keys())

    print("=" * 60)
    print("MEMORY-EFFICIENT DRIFTING GRATINGS ANALYSIS")
    print("=" * 60)
    print(f"Network: {net_name}")
    print(f"Option: {network_option}")
    print(f"Angles: {angles}")
    print(f"Conditions: {conditions}")

    # Setup output directory
    csv_files_dir = os.path.join(
        net_name, "metrics", "dg_L4_inh_silencing_power"
    )
    os.makedirs(csv_files_dir, exist_ok=True)

    # Output files
    output_path_csv = os.path.join(csv_files_dir, "dg_all_dirs_mua_power.csv")
    output_path_pickle = os.path.join(csv_files_dir, "dg_all_dirs_mua_power.pkl")
    
    # Initialize files
    header_written = False
    all_data_frames = []  # Store for pickle saving

    total_records = 0
    total_tasks = 0
    completed_tasks = 0
    failed_tasks = 0

    # Calculate total tasks
    for angle in angles:
        trials, _ = get_config_range(angle)
        total_tasks += len(trials) * len(conditions)

    print(f"Total tasks to process: {total_tasks}")
    print("CSV output:", output_path_csv)
    print("Pickle output:", output_path_pickle)

    start_time = time.time()

    # Process data in small chunks to avoid memory issues
    chunk_results = []
    chunk_size = 10  # Process 10 trials at a time

    for angle_idx, angle in enumerate(angles):
        print(f"\nProcessing angle {angle_idx+1}/{len(angles)}: {angle}")
        trials, num_trials = get_config_range(angle)

        for condition_idx, condition in enumerate(conditions):
            print(f"  Condition {condition_idx+1}/{len(conditions)}: {condition}")

            # Process trials in small chunks
            for trial_chunk_start in range(trials.start, trials.stop, chunk_size):
                trial_chunk_end = min(trial_chunk_start + chunk_size, trials.stop)
                trial_chunk = range(trial_chunk_start, trial_chunk_end)

                print(
                    f"    Processing trials {trial_chunk_start}-{trial_chunk_end-1}..."
                )

                chunk_data = []
                for trial in trial_chunk:
                    completed_tasks += 1

                    result = process_single_trial_grouped(
                        net_name, network_option, condition, trial, num_trials, angle
                    )
                    if result is not None and not result.empty:
                        chunk_data.append(result)
                        total_records += len(result)
                    else:
                        failed_tasks += 1

                    # Progress update
                    if completed_tasks % 50 == 0:
                        elapsed = time.time() - start_time
                        rate = completed_tasks / elapsed
                        eta = (total_tasks - completed_tasks) / rate if rate > 0 else 0
                        print(
                            f"      Progress: {completed_tasks}/{total_tasks} ({completed_tasks/total_tasks*100:.1f}%)"
                        )
                        print(
                            f"      Failed: {failed_tasks}, Records: {total_records}, ETA: {eta/60:.1f} min"
                        )

                # Combine chunk and append to file
                if chunk_data:
                    chunk_df = pd.concat(chunk_data, ignore_index=True)
                    
                    # Store original dataframe for pickle
                    all_data_frames.append(chunk_df.copy())
                    
                    # Prepare CSV version with arrays as strings
                    chunk_df_csv = chunk_df.copy()
                    
                    # Convert array columns to string representation to prevent truncation
                    array_columns = ['timestamps', 'f', 'mua', 'power', 'power_norm']
                    for col in array_columns:
                        if col in chunk_df_csv.columns:
                            chunk_df_csv[col] = chunk_df_csv[col].apply(lambda x: str(x.tolist()) if hasattr(x, 'tolist') else str(x))

                    # Append to CSV file
                    if not header_written:
                        chunk_df_csv.to_csv(output_path_csv, index=False, mode="w")
                        header_written = True
                    else:
                        chunk_df_csv.to_csv(
                            output_path_csv, index=False, mode="a", header=False
                        )

                    print(f"    Saved chunk with {len(chunk_df)} records")

                    # Clean up
                    del chunk_df, chunk_df_csv
                    del chunk_data
                    gc.collect()

    # Save complete dataset as pickle for full data preservation
    if all_data_frames:
        print("\nSaving complete dataset as pickle...")
        complete_df = pd.concat(all_data_frames, ignore_index=True)
        with open(output_path_pickle, 'wb') as f:
            pickle.dump(complete_df, f)
        
        # Clean up
        del all_data_frames, complete_df
        gc.collect()
    
    # Final summary
    elapsed_total = time.time() - start_time
    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Completed: {completed_tasks - failed_tasks}/{completed_tasks} tasks")
    print(f"Failed: {failed_tasks} tasks ({failed_tasks/completed_tasks*100:.1f}%)")
    print(f"Total records: {total_records}")
    
    # Get file sizes and report
    if os.path.exists(output_path_csv):
        csv_size = os.path.getsize(output_path_csv) / (1024 * 1024)  # Convert to MB
        print(f"CSV file size: {csv_size:.1f} MB")
        print(f"CSV output saved to: {output_path_csv}")
    
    if os.path.exists(output_path_pickle):
        pickle_size = os.path.getsize(output_path_pickle) / (1024 * 1024)  # Convert to MB
        print(f"Pickle file size: {pickle_size:.1f} MB")
        print(f"Pickle output saved to: {output_path_pickle}")
        print(f"\nNOTE: Use pickle file to load data with full array precision:")
        print(f"  import pickle")
        print(f"  with open('{output_path_pickle}', 'rb') as f:")
        print(f"      df = pickle.load(f)")
    print("=" * 60)

    return output_path_csv, output_path_pickle


def run_layer_analysis(net_name="core", network_option="checkpoint"):
    """Run layer-grouped analysis on saved data."""
    
    # Setup directories
    csv_files_dir = os.path.join(
        net_name, "metrics", "dg_L4_inh_silencing_power"
    )
    
    # Input file (saved from previous analysis)
    input_path = os.path.join(csv_files_dir, "dg_all_dirs_mua_power.pkl")
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        print("Please run the main analysis first to generate the data.")
        return None
    
    print("\n" + "="*60)
    print("LAYER-GROUPED ANALYSIS")
    print("="*60)
    print(f"Reading data from: {input_path}")
    
    # Load the saved data
    with open(input_path, 'rb') as f:
        df = pickle.load(f)
    
    print(f"Loaded {len(df)} records")
    
    # Group by layer instead of cell type and aggregate spike data
    print("Grouping by layer and aggregating spike data...")
    layer_grouped = df.groupby(["condition", "trial", "layer", "dir"], sort=False)["timestamps"].agg(list).to_frame().reset_index()
    
    print(f"Created {len(layer_grouped)} layer combinations")
    
    # Calculate power spectrum for each layer group
    print("Calculating power spectra...")
    layer_grouped[["f", "power", "mua"]] = layer_grouped.apply(
        ps_for_MUA_df_layer,
        bins=np.linspace(500, 3000, 1250),
        nperseg=500,
        axis=1,
        result_type="expand"
    )
    
    # Remove timestamps column as requested
    layer_analysis_df = layer_grouped.drop(columns=['timestamps'])
    
    # Save results
    output_path_csv = os.path.join(csv_files_dir, "dg_all_dirs_mua_power_layer_L4only_silence_inh.csv")
    output_path_pickle = os.path.join(csv_files_dir, "dg_all_dirs_mua_power_layer_L4only_silence_inh.pkl")
    
    # Save CSV with arrays as strings
    layer_df_csv = layer_analysis_df.copy()
    array_columns = ['f', 'power', 'mua']
    for col in array_columns:
        if col in layer_df_csv.columns:
            layer_df_csv[col] = layer_df_csv[col].apply(lambda x: str(x.tolist()) if hasattr(x, 'tolist') else str(x))
    
    layer_df_csv.to_csv(output_path_csv, index=False)
    
    # Save pickle with native arrays
    with open(output_path_pickle, 'wb') as f:
        pickle.dump(layer_analysis_df, f)
    
    # Report results
    csv_size = os.path.getsize(output_path_csv) / (1024 * 1024)
    pickle_size = os.path.getsize(output_path_pickle) / (1024 * 1024)
    
    print(f"\nLayer analysis complete!")
    print(f"Records: {len(layer_analysis_df)}")
    print(f"CSV file size: {csv_size:.1f} MB")
    print(f"Pickle file size: {pickle_size:.1f} MB")
    print(f"CSV saved to: {output_path_csv}")
    print(f"Pickle saved to: {output_path_pickle}")
    print("="*60)
    
    return output_path_csv, output_path_pickle


def main():
    """Main execution function."""

    parser = argparse.ArgumentParser(
        description="Memory-efficient drifting gratings analysis"
    )
    parser.add_argument("--net_name", default="core", help="Network name")
    parser.add_argument("--network_option", default="checkpoint", help="Network option")
    parser.add_argument(
        "--angles", nargs="+", default=None, help="Specific angles to process"
    )
    parser.add_argument(
        "--conditions", nargs="+", default=None, help="Specific conditions to process"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run quick test with subset of data"
    )

    args = parser.parse_args()

    # Test mode
    if args.test:
        print("Running in test mode with subset of data...")
        args.angles = ["theta0"]
        args.conditions = ["no perturb"]

    # Run main analysis
    result_csv_path, result_pickle_path = run_analysis_memory_efficient(
        net_name=args.net_name,
        network_option=args.network_option,
        angles=args.angles,
        conditions=args.conditions,
    )

    # Always run layer analysis after main analysis
    print("\nRunning layer-grouped analysis...")
    layer_csv_path, layer_pickle_path = run_layer_analysis(
        net_name=args.net_name,
        network_option=args.network_option
    )

    return result_csv_path, result_pickle_path, layer_csv_path, layer_pickle_path


if __name__ == "__main__":
    main()
