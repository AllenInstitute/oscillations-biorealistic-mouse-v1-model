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
DRIFTING_ANGLES = ["theta0", "theta45", "theta90", "theta135", "theta180", "theta225", "theta270", "theta315"]
NATURAL_SETS = ["set1", "set2", "set3", "set4", "set5", "set6", "set7", "set8"]

PERTURB_DICT = {
    "drifting grating": "8dir_10trials",
    "natural scenes": "natural_scenes_10trials",
    "natural movie one": "natural_movie_one_10trials",
    "natural movie two": "natural_movie_two_10trials",
}

def get_config_range(stimulus_param):
    """Get trial range and offset for angle or set."""
    # For drifting gratings (angles)
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

    # For natural stimuli (sets) - each set has 10 trials (0-9)
    set_map = {
        "set1": (range(0, 10), 0),
        "set2": (range(10, 20), 10),
        "set3": (range(20, 30), 20),
        "set4": (range(30, 40), 30),
        "set5": (range(40, 50), 40),
        "set6": (range(50, 60), 50),
        "set7": (range(60, 70), 60),
        "set8": (range(70, 80), 70),
    }

    # Check angle map first, then set map
    if stimulus_param in angle_map:
        return angle_map[stimulus_param]
    elif stimulus_param in set_map:
        return set_map[stimulus_param]
    else:
        return (range(0, 10), 0)

def build_file_path(net_name, network_option, condition, trial, stimulus_param=None):
    """Build configuration file path."""
    folder_name = PERTURB_DICT.get(condition, "drifting grating")
    
    # All conditions use the same structure: configs/{folder_name}_{network_option}/config_{trial}.json
    dir_name = "{}_{}" .format(folder_name, network_option)
    full_path = os.path.join(net_name, "configs", dir_name)
    return f"{full_path}/config_{trial}.json"

def ps_for_MUA_df(row, bins=np.linspace(500, 3000, 1250), nperseg=500):
    # power spectral analysis for population activity using welch's method
    # INPUTS:
    # row: a row of the dataframe
    # bins: bins for population activity, default is 5 ms
    # nperseg: nperseg for welch method, default is 100*5ms = 500ms
    # OUTPUTS:
    # f: frequency
    # s: power spectrum during stimulus presentation
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
    
    # Use the flattened all_spikes instead of the nested spikes
    (counts, bins) = np.histogram(all_spikes, bins=bins)
    binsize = bins[1] - bins[0]
    mua = counts / (binsize / 1e3)  # Hz
    
    f, s = scipy.signal.welch(
        mua, fs=1 / binsize * 1e3, nperseg=nperseg, scaling="spectrum"
    )
    return f, s, mua

def process_single_trial_grouped(net_name, network_option, condition, trial, num_trials, stimulus_param):
    """Process single trial and return grouped data directly to save memory."""
    
    try:
        file_path = build_file_path(net_name, network_option, condition, trial, stimulus_param)
        
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
            dir=stimulus_param,
            cell_layer=spike_df['layer'] + " " + spike_df['cell_type']
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
            spike_df.groupby(["condition", "trial", "layer", "cell", "dir"], sort=False)["timestamps"]
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
        print(f"Error processing {condition}, trial {trial}, stimulus_param {stimulus_param}: {str(e)[:100]}")
        return None

def run_analysis_memory_efficient(net_name="core", network_option="checkpoint", 
                                 angles=None, sets=None, conditions=None):
    """Run the analysis with memory efficiency."""
    
    if angles is None:
        angles = DRIFTING_ANGLES
    if sets is None:
        sets = NATURAL_SETS
    if conditions is None:
        conditions = list(PERTURB_DICT.keys())
    
    print("="*60)
    print("MEMORY-EFFICIENT OTHER VISUAL STIMULI ANALYSIS")
    print("="*60)
    print(f"Network: {net_name}")
    print(f"Option: {network_option}")
    print(f"Angles: {angles}")
    print(f"Sets: {sets}")
    print(f"Conditions: {conditions}")
    
    # Setup output directory
    csv_files_dir = os.path.join(net_name, "metrics", "other_visual_stim_power")
    os.makedirs(csv_files_dir, exist_ok=True)
    
    # Output paths for both CSV and pickle
    output_path_csv = os.path.join(csv_files_dir, "other_visual_stim_all_dirs_mua_power.csv")
    output_path_pickle = os.path.join(csv_files_dir, "other_visual_stim_all_dirs_mua_power.pkl")
    output_path = output_path_csv  # Keep backward compatibility
    
    # Initialize CSV with header
    header_written = False
    
    total_records = 0
    total_tasks = 0
    completed_tasks = 0
    failed_tasks = 0
    
    # Calculate total tasks
    for condition in conditions:
        if condition == "drifting grating":
            for angle in angles:
                trials, _ = get_config_range(angle)
                total_tasks += len(trials)
        else:
            for set_param in sets:
                trials, _ = get_config_range(set_param)
                total_tasks += len(trials)
    
    print(f"\nTotal tasks to process: {total_tasks}")
    print(f"CSV file: {output_path_csv}")
    print(f"Pickle file: {output_path_pickle}")
    
    start_time = time.time()
    
    # Process data in small chunks to avoid memory issues
    chunk_results = []
    chunk_size = 10  # Process 10 trials at a time
    
    for condition_idx, condition in enumerate(conditions):
        print(f"\nProcessing condition {condition_idx+1}/{len(conditions)}: {condition}")
        
        # Determine stimulus parameters based on condition
        if condition == "drifting grating":
            stimulus_params = angles
            param_type = "angle"
        else:
            stimulus_params = sets
            param_type = "set"
        
        for param_idx, stimulus_param in enumerate(stimulus_params):
            print(f"  Processing {param_type} {param_idx+1}/{len(stimulus_params)}: {stimulus_param}")
            trials, num_trials = get_config_range(stimulus_param)
            
            # Process trials in small chunks
            for trial_chunk_start in range(trials.start, trials.stop, chunk_size):
                trial_chunk_end = min(trial_chunk_start + chunk_size, trials.stop)
                trial_chunk = range(trial_chunk_start, trial_chunk_end)
                
                print(f"    Processing trials {trial_chunk_start}-{trial_chunk_end-1}...")
                
                chunk_data = []
                for trial in trial_chunk:
                    completed_tasks += 1
                    
                    result = process_single_trial_grouped(net_name, network_option, condition, 
                                                        trial, num_trials, stimulus_param)
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
                        print(f"      Progress: {completed_tasks}/{total_tasks} ({completed_tasks/total_tasks*100:.1f}%)")
                        print(f"      Failed: {failed_tasks}, Records: {total_records}, ETA: {eta/60:.1f} min")
                
                # Combine chunk and append to file
                if chunk_data:
                    chunk_df = pd.concat(chunk_data, ignore_index=True)
                    
                    # Create CSV version with string arrays
                    chunk_df_csv = chunk_df.copy()
                    array_columns = ['timestamps', 'f', 'mua', 'power', 'power_norm']
                    for col in array_columns:
                        if col in chunk_df_csv.columns:
                            chunk_df_csv[col] = chunk_df_csv[col].apply(
                                lambda x: ', '.join(map(str, x)) if isinstance(x, (list, np.ndarray)) else str(x)
                            )
                    
                    # Save to CSV (string format)
                    if not header_written:
                        chunk_df_csv.to_csv(output_path_csv, index=False, mode="w")
                        header_written = True
                    else:
                        chunk_df_csv.to_csv(
                            output_path_csv, index=False, mode="a", header=False
                        )
                    
                    # Save to pickle (native format) - append mode for pickle
                    if os.path.exists(output_path_pickle) and header_written:
                        # Load existing data
                        with open(output_path_pickle, 'rb') as f:
                            existing_df = pickle.load(f)
                        # Combine with new data
                        combined_df = pd.concat([existing_df, chunk_df], ignore_index=True)
                        with open(output_path_pickle, 'wb') as f:
                            pickle.dump(combined_df, f)
                    else:
                        # First write
                        with open(output_path_pickle, 'wb') as f:
                            pickle.dump(chunk_df, f)
                    
                    print(f"    Saved chunk with {len(chunk_df)} records")
                    
                    # Clean up
                    del chunk_df, chunk_df_csv
                    del chunk_data
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
    print(f"CSV file: {output_path_csv}")
    print(f"Pickle file: {output_path_pickle}")
    if os.path.exists(output_path_csv):
        print(f"CSV file size: {os.path.getsize(output_path_csv)/1024**2:.1f} MB")
    if os.path.exists(output_path_pickle):
        print(f"Pickle file size: {os.path.getsize(output_path_pickle)/1024**2:.1f} MB")
    
    return output_path_csv, output_path_pickle

def run_layer_analysis(net_name="core", network_option="checkpoint"):
    """Run layer-grouped analysis on saved MUA power data."""
    
    # Setup paths
    csv_files_dir = os.path.join(net_name, "metrics", "other_visual_stim_power")
    input_file_path = os.path.join(csv_files_dir, "other_visual_stim_all_dirs_mua_power.pkl")
    
    output_path_csv = os.path.join(csv_files_dir, "other_visual_stim_all_dirs_mua_power_layer.csv")
    output_path_pickle = os.path.join(csv_files_dir, "other_visual_stim_all_dirs_mua_power_layer.pkl")
    
    print("\nRunning layer-grouped analysis...")
    print(f"Input file: {input_file_path}")
    print(f"Output CSV: {output_path_csv}")
    print(f"Output Pickle: {output_path_pickle}")
    
    # Load data
    if not os.path.exists(input_file_path):
        print(f"Error: Input file not found: {input_file_path}")
        return None
    
    print("Loading saved MUA power data...")
    with open(input_file_path, 'rb') as f:
        mua_power_all = pickle.load(f)
    # mua_power_all = pd.read_pickle(input_file_path)
    print(f"Loaded {len(mua_power_all)} records")
    
    # Group by layer instead of cell
    mua_layer = (
        mua_power_all.groupby(["condition", "trial", "layer", "dir"], sort=False)["timestamps"].agg(list).to_frame().reset_index()
    )
    
    print(f"Grouped into {len(mua_layer)} layer combinations")
    
    # Set parameters
    bins = np.linspace(500, 3000, 1250)  # binsize: (3000-500)/1249 ≈ 2ms
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
            mua_layer_csv[col] = mua_layer_csv[col].apply(lambda x: str(x.tolist()) if hasattr(x, 'tolist') else str(x))
    
    # Save to CSV (string format)
    mua_layer_csv.to_csv(output_path_csv, index=False)
    
    # Save to pickle (native format)
    with open(output_path_pickle, 'wb') as f:
        pickle.dump(mua_layer_final, f)
    
    print(f"\nLayer analysis complete!")
    print(f"Processed {len(mua_layer_final)} layer combinations")
    if os.path.exists(output_path_csv):
        print(f"CSV file size: {os.path.getsize(output_path_csv)/1024**2:.1f} MB")
    if os.path.exists(output_path_pickle):
        print(f"Pickle file size: {os.path.getsize(output_path_pickle)/1024**2:.1f} MB")
    
    return output_path_csv, output_path_pickle

def main():
    """Main execution function."""
    
    parser = argparse.ArgumentParser(description="Memory-efficient drifting gratings analysis")
    parser.add_argument("--net_name", default="core", help="Network name")
    parser.add_argument("--network_option", default="checkpoint", help="Network option")
    parser.add_argument("--angles", nargs="+", default=None, 
                      help="Specific angles to process")
    parser.add_argument("--sets", nargs="+", default=None, 
                      help="Specific sets to process")
    parser.add_argument("--conditions", nargs="+", default=None,
                      help="Specific conditions to process")
    parser.add_argument("--test", action="store_true", 
                      help="Run quick test with subset of data")
    parser.add_argument("--skip-main", action="store_true",
                      help="Skip main analysis and only run layer analysis")
    
    args = parser.parse_args()
    
    # Test mode
    if args.test:
        print("Running in test mode with subset of data...")
        args.angles = ["theta0"]
        args.sets = ["set1"]
        args.conditions = ["natural scenes"]
    
    # Initialize return values
    result_csv_path, result_pickle_path = None, None
    layer_csv_path, layer_pickle_path = None, None
    
    # Run main analysis (unless skipped)
    if not getattr(args, 'skip_main', False):
        result_csv_path, result_pickle_path = run_analysis_memory_efficient(
            net_name=args.net_name,
            network_option=args.network_option,
            angles=args.angles,
            sets=args.sets,
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
