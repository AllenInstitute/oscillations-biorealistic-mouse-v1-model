#!/usr/bin/env python3
"""
Memory-efficient analysis script for drifting gratings — L6 model variants.
Processes data in chunks to avoid memory issues.

Silencing condition: L6 only (all other layers left active).

Supported model variants:
    L6-as-L4, L6-syn-as-L4-syn, L6-syn-as-L4-syn-PSP, L6-syn-as-L4-syn-v2

Usage:
    python analysis_dg_layer_silencing_power_L6_model_variants.py --model_variant L6-as-L4
    python analysis_dg_layer_silencing_power_L6_model_variants.py --model_variant L6-syn-as-L4-syn --net_name core_L6-syn-as-L4-syn
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
DRIFTING_ANGLES = ["theta0", "theta45", "theta90", "theta135", "theta180", "theta225", "theta270", "theta315"]

PERTURB_DICT = {
    # "no perturb": "",
    # "L1": "_opto_layer_silencing_L23_L4_L5_L6_-2000",
    # "L2/3": "_opto_layer_silencing_L1_L4_L5_L6_-2000",
    # "L4": "_opto_layer_silencing_L1_L23_L5_L6_-2000",
    # "L5": "_opto_layer_silencing_L1_L23_L4_L6_-2000",
    "L6": "_opto_layer_silencing_L1_L23_L4_L5_-2000",
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
        "theta315": (range(70, 80), 70)
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
    mua = counts / (binsize / 1e3) # Hz - normalized by thr total number of neurons n_neuron *
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

def process_single_trial_grouped(net_name, network_option, condition, trial, num_trials, angle):
    """Process single trial and return grouped data directly to save memory."""
    file_path = build_file_path(net_name, network_option, condition, trial)

    try:
        if not os.path.exists(file_path):
            return None, {
                "condition": condition,
                "trial": trial,
                "dir": angle,
                "file_path": file_path,
                "reason": "missing_config",
            }

        # Suppress verbose output from data_organize
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            _, spike_df = data_organize(file_path, t_min=500, t_max=3000)
        finally:
            sys.stdout = old_stdout

        if spike_df is None or spike_df.empty:
            return None, {
                "condition": condition,
                "trial": trial,
                "dir": angle,
                "file_path": file_path,
                "reason": "empty_spike_df",
            }

        # Add metadata
        spike_df = spike_df.assign(
            condition=condition,
            trial=trial - num_trials,
            dir=angle,
            cell_layer=spike_df['layer'] + " " + spike_df['cell_type']
        )

        #
        spike_df[["layer", "cell"]] = spike_df.apply(
            lambda x: x["cell_layer"].split(" "), axis=1, result_type="expand"
        )

        # Group by cell type and get multi-unit activity
        mua_power_df = (
            spike_df.groupby(["condition", "trial", "layer", "cell", "dir"], sort=False)["timestamps"]
            .agg(list)
            .to_frame()
            .reset_index()
        )

        # Calculate the power spectrum
        mua_power_df[["f", "mua", "power", "power_norm"]] = mua_power_df.apply(
            ps_for_MUA_df,
            axis=1,
            result_type="expand",
        )

        # Clean up original dataframe
        del spike_df
        gc.collect()

        return mua_power_df, None

    except Exception as e:
        return None, {
            "condition": condition,
            "trial": trial,
            "dir": angle,
            "file_path": file_path,
            "reason": f"exception: {str(e)[:200]}",
        }

def run_analysis_memory_efficient(net_name="core", network_option="checkpoint",
                                 angles=None, conditions=None):
    """Run the analysis with memory efficiency."""

    if angles is None:
        angles = DRIFTING_ANGLES
    if conditions is None:
        conditions = list(PERTURB_DICT.keys())

    print("="*60)
    print("MEMORY-EFFICIENT DRIFTING GRATINGS ANALYSIS")
    print("="*60)
    print(f"Network: {net_name}")
    print(f"Option: {network_option}")
    print(f"Angles: {angles}")
    print(f"Conditions: {conditions}")

    # Setup output directory
    csv_files_dir = os.path.join(net_name, "metrics", "dg_layer_silencing_power")
    os.makedirs(csv_files_dir, exist_ok=True)

    # Output paths for both CSV and pickle
    output_path_csv = os.path.join(csv_files_dir, "dg_all_dirs_mua_power.csv")
    output_path_pickle = os.path.join(csv_files_dir, "dg_all_dirs_mua_power.pkl")

    # Initialize files
    header_written = False
    all_data_frames = []  # Store for pickle saving

    total_records = 0
    total_tasks = 0
    completed_tasks = 0
    failed_tasks = 0
    failed_details = []

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

                print(f"    Processing trials {trial_chunk_start}-{trial_chunk_end-1}...")

                chunk_data = []
                for trial in trial_chunk:
                    completed_tasks += 1

                    result, fail_info = process_single_trial_grouped(
                        net_name, network_option, condition, trial, num_trials, angle
                    )

                    if result is not None and not result.empty:
                        chunk_data.append(result)
                        total_records += len(result)
                    else:
                        failed_tasks += 1
                        if fail_info is not None:
                            failed_details.append(fail_info)
                            print(
                                "      FAILED "
                                f"[{fail_info['reason']}] "
                                f"condition={fail_info['condition']} "
                                f"dir={fail_info['dir']} "
                                f"trial={fail_info['trial']} "
                                f"file={fail_info['file_path']}"
                            )

                    # Progress update
                    if completed_tasks % 50 == 0:
                        elapsed = time.time() - start_time
                        rate = completed_tasks / elapsed
                        eta = (total_tasks - completed_tasks) / rate if rate > 0 else 0
                        print(f"      Progress: {completed_tasks}/{total_tasks} ({completed_tasks/total_tasks*100:.1f}%)")
                        print(f"      Failed: {failed_tasks}, Records: {total_records}, ETA: {eta/60:.1f} min")

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

                    # Save to CSV (string format)
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

    if failed_details:
        failed_log_path = os.path.join(csv_files_dir, "dg_failed_tasks.csv")
        pd.DataFrame(failed_details).to_csv(failed_log_path, index=False)
        print(f"Failed details saved to: {failed_log_path}")

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

    # Setup paths
    csv_files_dir = os.path.join(net_name, "metrics", "dg_layer_silencing_power")
    input_file_path = os.path.join(csv_files_dir, "dg_all_dirs_mua_power.pkl")

    output_path_csv = os.path.join(csv_files_dir, "dg_all_dirs_mua_power_layer.csv")
    output_path_pickle = os.path.join(csv_files_dir, "dg_all_dirs_mua_power_layer.pkl")

    print("\nRunning layer-grouped analysis...")
    print(f"Input file: {input_file_path}")
    print(f"Output CSV: {output_path_csv}")
    print(f"Output Pickle: {output_path_pickle}")

    # Load data
    if not os.path.exists(input_file_path):
        print(f"Error: Input file not found: {input_file_path}")
        return None

    print("Loading saved MUA power data...")
    mua_power_all = pd.read_pickle(input_file_path)
    print(f"Loaded {len(mua_power_all)} records")

    # Group by layer instead of cell
    mua_layer = (
        mua_power_all.groupby(["condition", "trial", "layer", "dir"])["timestamps"]
        .agg(list)
        .to_frame()
    )
    mua_layer.reset_index(inplace=True)

    print(f"Grouped into {len(mua_layer)} layer combinations")

    # Set parameters
    bins = np.linspace(500, 3000, 1250)  # binsize: (3000-500)/1250 = 2ms
    nperseg = 500  # segment length

    # Apply analysis
    print("Computing layer-grouped power spectra...")
    mua_layer[["f", "power", "mua"]] = mua_layer.apply(
        ps_for_MUA_df_layer,
        bins=bins,
        nperseg=nperseg,
        axis=1,
        result_type="expand",
    )

    # Remove timestamps column (don't save it)
    mua_layer_final = mua_layer.drop(columns=['timestamps'])

    # Save results
    print("Saving results...")

    # Create CSV version with string arrays
    mua_layer_csv = mua_layer_final.copy()
    array_columns = ['f', 'power', 'mua']
    for col in array_columns:
        if col in mua_layer_csv.columns:
            mua_layer_csv[col] = mua_layer_csv[col].apply(
                lambda x: ', '.join(map(str, x)) if isinstance(x, (list, np.ndarray)) else str(x)
            )

    # Save to CSV (string format)
    mua_layer_csv.to_csv(output_path_csv, index=False)

    # Save to pickle (native format)
    with open(output_path_pickle, 'wb') as f:
        pickle.dump(mua_layer_final, f)
    # Report results
    csv_size = os.path.getsize(output_path_csv) / (1024 * 1024)
    pickle_size = os.path.getsize(output_path_pickle) / (1024 * 1024)

    print(f"\nLayer analysis complete!")
    print(f"Records: {len(mua_layer_csv)}")
    print(f"CSV file size: {csv_size:.1f} MB")
    print(f"Pickle file size: {pickle_size:.1f} MB")
    print(f"CSV saved to: {output_path_csv}")
    print(f"Pickle saved to: {output_path_pickle}")
    print("="*60)

    return output_path_csv, output_path_pickle

def main():
    """Main execution function."""

    parser = argparse.ArgumentParser(
        description="Memory-efficient drifting gratings analysis — L6 model variants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Supported model variants:
            L6-as-L4  L6-syn-as-L4-syn  L6-syn-as-L4-syn-PSP  L6-syn-as-L4-syn-v2
        """
    )
    parser.add_argument(
        "--model_variant", default="L6-as-L4",
        help="Model variant suffix (e.g. L6-as-L4). "
             "Sets net_name to core_<model_variant> unless --net_name is given."
    )
    parser.add_argument(
        "--net_name", default=None,
        help="Override network directory name (default: core_<model_variant>)"
    )
    parser.add_argument("--network_option", default="checkpoint", help="Network option")
    parser.add_argument("--angles", nargs="+", default=None,
                      help="Specific angles to process")
    parser.add_argument("--conditions", nargs="+", default=None,
                      help="Specific conditions to process")
    parser.add_argument("--test", action="store_true",
                      help="Run quick test with subset of data")
    parser.add_argument("--skip-main", action="store_true",
                      help="Skip main analysis and only run layer analysis")

    args = parser.parse_args()

    if args.net_name is None:
        args.net_name = f"core_{args.model_variant}"

    # Test mode
    if args.test:
        print("Running in test mode with subset of data...")
        args.angles = ["theta0"]
        args.conditions = list(PERTURB_DICT.keys())[:1]

    # Initialize return values
    result_csv_path, result_pickle_path = None, None
    layer_csv_path, layer_pickle_path = None, None

    # Run main analysis (unless skipped)
    if not getattr(args, 'skip_main', False):
        result_csv_path, result_pickle_path = run_analysis_memory_efficient(
            net_name=args.net_name,
            network_option=args.network_option,
            angles=args.angles,
            conditions=args.conditions
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
