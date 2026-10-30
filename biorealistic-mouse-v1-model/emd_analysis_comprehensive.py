#!/usr/bin/env python3
"""
Comprehensive EMD Analysis Script
Performs EMD analysis for each trial and angle, saves data, and generates PDF report.
Based on analysis from plot_laminar_power_L4only.ipynb cell 19.
"""

import os
import glob
import argparse
from multiprocessing import Pool
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import scipy
from scipy.stats import ttest_ind
import seaborn as sns
from math import sqrt
import re
from matplotlib.ticker import ScalarFormatter
import matplotlib.ticker as mticker
from matplotlib.backends.backend_pdf import PdfPages
import pickle
import json
from datetime import datetime

import emd

# Configure matplotlib for better PDF output
plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.size"] = 10

def str2list(str_time):
    """Convert string representation of list to numpy array"""
    str_time = str_time[1:-1]
    array_list = str_time.strip(",").split(", ")
    return np.stack([float(ii) for ii in array_list])

def load_and_prepare_data():
    """Load and prepare the MUA power data"""
    print("Loading data...")
    
    # Configuration
    freq = "dg_all_dirs_mua_power_layer_L4only_silence_inh"
    net_name = "core"
    csv_files_dir = os.path.join(
        net_name, "metrics", "dg_L4_inh_silencing_power"
    )
    
    # Load data
    mua_power_all = pd.read_csv(os.path.join(csv_files_dir, f"{freq}.csv"))
    
    # Convert string representations to arrays
    mua_power_all["mua"] = mua_power_all["mua"].apply(str2list)
    mua_power_all["power"] = mua_power_all["power"].apply(str2list)
    mua_power_all["f"] = mua_power_all["f"].apply(str2list)
    
    # Filter for L4 layer and L4 condition
    mua_power_all_L4 = mua_power_all.query("layer == 'L4' & condition == 'L4'")[
        ["trial", "layer", "dir", "f", "mua", "power"]
    ]
    
    print(f"Data loaded: {len(mua_power_all_L4)} records")
    return mua_power_all_L4

def assess_all_harmonic_pairs(IP, IF, IA, num_segments=18):
    """
    Test every IMF pair for a harmonic relationship.

    emd.imftools.assess_harmonic_criteria(base_imf=k) only compares IMFs 0..k-1
    against IMF k, so we loop k over 1..n_imfs-1 to cover all pairs, always taking
    the slower IMF of the pair as the potential fundamental.

    Returns a long-format DataFrame with 1-indexed columns 'harmonic_imf'
    (candidate harmonic, faster IMF) and 'fundamental_imf' (base, slower IMF),
    followed by the criteria columns returned by assess_harmonic_criteria.
    """
    frames = []
    for base_imf in range(1, IP.shape[1]):
        df = emd.imftools.assess_harmonic_criteria(
            IP, IF, IA, num_segments=num_segments, base_imf=base_imf, print_result=False
        )
        df.insert(0, 'harmonic_imf', np.arange(1, base_imf + 1))
        df.insert(1, 'fundamental_imf', base_imf + 1)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

def _harmonic_pairs_from_pickle(pkl_path):
    """Worker: compute all-pairs harmonic criteria from a saved EMD results pickle"""
    with open(pkl_path, 'rb') as f:
        r = pickle.load(f)
    if 'error' in r:
        return None
    IP, IF, IA = (np.asarray(r[k]) for k in
                  ('instantaneous_phase', 'instantaneous_frequency', 'instantaneous_amplitude'))
    df = assess_all_harmonic_pairs(IP, IF, IA)
    df.insert(0, 'trial', r['trial'])
    df.insert(1, 'angle', r['angle'])
    print(f"Harmonic pairs done for trial {r['trial']}, angle {r['angle']}")
    return df

def save_harmonic_pairs_table(frames, output_dir):
    """Concatenate per-recording all-pairs tables and save them as CSV"""
    table = pd.concat([f for f in frames if f is not None], ignore_index=True)
    out_file = os.path.join(output_dir, 'harmonic_criteria_all_pairs.csv')
    table.to_csv(out_file, index=False)
    print(f"All-pairs harmonic criteria: {out_file} ({len(table)} rows)")
    return table

def run_harmonic_pairs_from_pickles(output_dir, n_workers):
    """Compute all-pairs harmonic criteria from existing pickles (pickles are not modified)"""
    pkl_files = sorted(glob.glob(os.path.join(output_dir, 'emd_results_trial_*_angle_*.pkl')))
    print(f"Computing all-pairs harmonic criteria for {len(pkl_files)} recordings "
          f"with {n_workers} workers...")
    with Pool(n_workers) as pool:
        frames = pool.map(_harmonic_pairs_from_pickle, pkl_files)
    return save_harmonic_pairs_table(frames, output_dir)

def perform_emd_analysis(mua_signal, fs, trial_id, angle, output_dir):
    """
    Perform EMD analysis on a single MUA signal
    
    Parameters:
    - mua_signal: MUA time series data
    - fs: Sampling frequency
    - trial_id: Trial identifier
    - angle: Stimulus angle/direction
    - output_dir: Output directory for saving data
    
    Returns:
    - Dictionary containing analysis results
    """
    
    results = {
        'trial': trial_id,
        'angle': angle,
        'fs': fs,
        'analysis_timestamp': datetime.now().isoformat()
    }
    
    try:
        # Perform EMD sift
        imf, mask_freqs = emd.sift.iterated_mask_sift(
            mua_signal, 
            sample_rate=fs, 
            ret_mask_freq=True, 
            max_imfs=5
        )
        
        results['mask_freqs'] = mask_freqs.tolist() if hasattr(mask_freqs, 'tolist') else mask_freqs
        results['n_imfs'] = imf.shape[1]
        
        # Compute Hilbert transform
        IP, IF, IA = emd.spectra.frequency_transform(imf, fs, "hilbert")
        
        # Test harmonic conditions for every IMF pair (slower IMF as fundamental)
        df_pairs = assess_all_harmonic_pairs(IP, IF, IA, num_segments=18)
        results['harmonic_criteria_all_pairs'] = df_pairs.to_dict('list')

        # Keep the original IMF-1..4 vs IMF-5 (base_imf=4) table for backward compatibility
        df = (df_pairs.query("fundamental_imf == 5")
              .drop(columns=['harmonic_imf', 'fundamental_imf'])
              .reset_index(drop=True))
        results['harmonic_criteria'] = df.to_dict()
        
        # Define frequency bins for HHT
        freq_edges, freq_centres = emd.spectra.define_hist_bins(0, 100, 128, 'linear')
        
        # Amplitude weighted HHT per IMF
        f, spec_weighted = emd.spectra.hilberthuang(IF, IA, freq_edges, sum_imfs=False)
        
        # Unweighted HHT per IMF
        f, spec_unweighted = emd.spectra.hilberthuang(IF, np.ones_like(IA), freq_edges, sum_imfs=False)
        
        # Store spectral results
        results['freq_centres'] = freq_centres.tolist()
        results['spec_weighted'] = spec_weighted.tolist()
        results['spec_unweighted'] = spec_unweighted.tolist()
        results['imf_data'] = imf.tolist()
        results['instantaneous_phase'] = IP.tolist()
        results['instantaneous_frequency'] = IF.tolist()
        results['instantaneous_amplitude'] = IA.tolist()
        
        # Save individual results
        output_file = os.path.join(output_dir, f'emd_results_trial_{trial_id}_angle_{angle}.pkl')
        with open(output_file, 'wb') as f:
            pickle.dump(results, f)
            
        print(f"Analysis completed for trial {trial_id}, angle {angle}")
        return results
        
    except Exception as e:
        print(f"Error in EMD analysis for trial {trial_id}, angle {angle}: {str(e)}")
        results['error'] = str(e)
        return results

def create_emd_figure(results, fs):
    """Create comprehensive EMD figure for a single trial/angle"""
    
    if 'error' in results:
        # Create error figure
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        ax.text(0.5, 0.5, f"Error in analysis:\n{results['error']}", 
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
        ax.set_title(f"Trial {results['trial']}, Angle {results['angle']}° - Analysis Error")
        return fig
    
    # Create comprehensive figure
    fig = plt.figure(figsize=(15, 10))
    
    # Add trial and angle information at the top
    fig.suptitle(f"EMD Analysis - Trial {results['trial']}, Angle {results['angle']}°", 
                 fontsize=16, y=0.95)
    
    # Plot IMFs (top half)
    n_imfs = min(5, results['n_imfs'])
    
    # Create subplots for IMFs
    gs1 = fig.add_gridspec(n_imfs + 1, 2, left=0.1, right=0.95, top=0.85, bottom=0.55, 
                          width_ratios=[3, 1], hspace=0.3)
    
    # Plot original signal and IMFs
    imf_data = np.array(results['imf_data'])
    time_samples = min(4 * fs, imf_data.shape[0])  # Show first 4 seconds
    time_vect = np.linspace(0, time_samples/fs, time_samples)
    
    # Original signal (sum of IMFs)
    ax_orig = fig.add_subplot(gs1[0, 0])
    original_signal = np.sum(imf_data[:time_samples, :], axis=1)
    ax_orig.plot(time_vect, original_signal, 'k-', linewidth=1)
    ax_orig.set_title('Original Signal (Sum of IMFs)')
    ax_orig.set_ylabel('Amplitude')
    ax_orig.grid(True, alpha=0.3)
    
    # Individual IMFs
    colors = plt.cm.Set1(np.linspace(0, 1, n_imfs))
    for i in range(n_imfs):
        ax_imf = fig.add_subplot(gs1[i + 1, 0])
        ax_imf.plot(time_vect, imf_data[:time_samples, i], color=colors[i], linewidth=1)
        ax_imf.set_title(f'IMF {i + 1}')
        ax_imf.set_ylabel('Amplitude')
        ax_imf.grid(True, alpha=0.3)
        if i == n_imfs - 1:
            ax_imf.set_xlabel('Time (s)')
    
    # Frequency analysis subplot
    ax_freq = fig.add_subplot(gs1[:, 1])
    mask_freqs = results.get('mask_freqs', [])
    if mask_freqs:
        mask_freqs_hz = np.array(mask_freqs) if isinstance(mask_freqs, list) else mask_freqs
        bars = ax_freq.barh(range(len(mask_freqs_hz)), mask_freqs_hz, color=colors[:len(mask_freqs_hz)])
        ax_freq.set_yticks(range(len(mask_freqs_hz)))
        ax_freq.set_yticklabels([f'IMF {i+1}' for i in range(len(mask_freqs_hz))])
        ax_freq.set_xlabel('Frequency (Hz)')
        ax_freq.set_title('Mask Frequencies')
        ax_freq.grid(True, alpha=0.3)
        
        # Add frequency value labels on the bars
        for i, (bar, freq_val) in enumerate(zip(bars, mask_freqs_hz)):
            ax_freq.text(bar.get_width() + max(mask_freqs_hz) * 0.01, bar.get_y() + bar.get_height()/2, 
                        f'{freq_val:.1f} Hz', va='center', ha='left', fontsize=8)
    
    # HHT plots (bottom half)
    gs2 = fig.add_gridspec(1, 2, left=0.1, right=0.95, top=0.45, bottom=0.1, hspace=0.4)
    
    freq_centres = np.array(results['freq_centres'])
    spec_unweighted = np.array(results['spec_unweighted'])
    spec_weighted = np.array(results['spec_weighted'])
    
    # Unweighted HHT
    ax_unw = fig.add_subplot(gs2[0, 0])
    for i in range(min(5, spec_unweighted.shape[1])):
        ax_unw.plot(freq_centres, spec_unweighted[:, i], label=f'IMF-{i+1}', color=colors[i])
    ax_unw.set_xlim(0, 100)
    ax_unw.set_xlabel('Frequency (Hz)')
    ax_unw.set_ylabel('Count')
    ax_unw.set_title('Unweighted Hilbert-Huang Transform')
    ax_unw.legend(fontsize=8)
    ax_unw.grid(True, alpha=0.3)
    
    # Weighted HHT
    ax_w = fig.add_subplot(gs2[0, 1])
    for i in range(min(5, spec_weighted.shape[1])):
        ax_w.plot(freq_centres, spec_weighted[:, i], label=f'IMF-{i+1}', color=colors[i])
    ax_w.set_xlim(0, 100)
    ax_w.set_xlabel('Frequency (Hz)')
    ax_w.set_ylabel('Power')
    ax_w.set_title('IA-weighted Hilbert-Huang Transform')
    ax_w.legend(fontsize=8)
    ax_w.grid(True, alpha=0.3)
    
    plt.subplots_adjust(hspace=0.3, wspace=0.3)
    return fig

def generate_summary_statistics(all_results):
    """Generate summary statistics across all trials and angles"""
    
    summary = {
        'total_analyses': int(len(all_results)),
        'successful_analyses': int(len([r for r in all_results if 'error' not in r])),
        'failed_analyses': int(len([r for r in all_results if 'error' in r])),
        'unique_trials': int(len(set([r['trial'] for r in all_results if 'error' not in r]))),
        'unique_angles': int(len(set([r['angle'] for r in all_results if 'error' not in r])))
    }
    
    # Collect mask frequencies
    successful_results = [r for r in all_results if 'error' not in r]
    if successful_results:
        mask_freqs_all = []
        n_imfs_all = []
        
        for result in successful_results:
            if 'mask_freqs' in result and result['mask_freqs']:
                mask_freqs_all.extend(result['mask_freqs'])
            if 'n_imfs' in result:
                n_imfs_all.append(result['n_imfs'])
        
        if mask_freqs_all:
            summary['mask_freq_mean'] = float(np.mean(mask_freqs_all))
            summary['mask_freq_std'] = float(np.std(mask_freqs_all))
            summary['mask_freq_range'] = [float(np.min(mask_freqs_all)), float(np.max(mask_freqs_all))]
        
        if n_imfs_all:
            summary['n_imfs_mean'] = float(np.mean(n_imfs_all))
            summary['n_imfs_range'] = [int(np.min(n_imfs_all)), int(np.max(n_imfs_all))]
    
    return summary

def create_summary_figure(summary, all_results):
    """Create summary figure showing statistics across all analyses"""
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('EMD Analysis Summary', fontsize=16)
    
    successful_results = [r for r in all_results if 'error' not in r]
    
    # Analysis success rate
    ax1 = axes[0, 0]
    labels = ['Successful', 'Failed']
    sizes = [summary['successful_analyses'], summary['failed_analyses']]
    colors = ['green', 'red']
    ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Analysis Success Rate')
    
    # Number of IMFs distribution
    ax2 = axes[0, 1]
    if successful_results:
        n_imfs_list = [r.get('n_imfs', 0) for r in successful_results]
        ax2.hist(n_imfs_list, bins=range(1, max(n_imfs_list) + 2), alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Number of IMFs')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Distribution of Number of IMFs')
        ax2.grid(True, alpha=0.3)
    
    # Mask frequencies distribution
    ax3 = axes[1, 0]
    if successful_results:
        mask_freqs_all = []
        for result in successful_results:
            if 'mask_freqs' in result and result['mask_freqs']:
                # Convert to Hz
                freqs_hz = np.array(result['mask_freqs']) * result['fs']
                mask_freqs_all.extend(freqs_hz)
        
        if mask_freqs_all:
            ax3.hist(mask_freqs_all, bins=20, alpha=0.7, edgecolor='black')
            ax3.set_xlabel('Mask Frequency (Hz)')
            ax3.set_ylabel('Frequency')
            ax3.set_title('Distribution of Mask Frequencies')
            ax3.grid(True, alpha=0.3)
    
    # Trial vs Angle heatmap
    ax4 = axes[1, 1]
    if successful_results:
        trials = [r['trial'] for r in successful_results]
        angles = [r['angle'] for r in successful_results]
        
        trial_angle_df = pd.DataFrame({'trial': trials, 'angle': angles})
        pivot_table = trial_angle_df.groupby(['trial', 'angle']).size().unstack(fill_value=0)
        
        if not pivot_table.empty:
            sns.heatmap(pivot_table, annot=True, fmt='d', cmap='Blues', ax=ax4)
            ax4.set_title('Successful Analyses by Trial and Angle')
            ax4.set_xlabel('Angle')
            ax4.set_ylabel('Trial')
    
    plt.subplots_adjust(hspace=0.4, wspace=0.3)
    return fig

def main():
    """Main execution function"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harmonics-only', action='store_true',
                        help='Skip the EMD sift and only compute all-pairs harmonic criteria '
                             'from the existing pickles in core/emd_analysis_output/')
    parser.add_argument('--n-workers', type=int, default=8,
                        help='Parallel workers for --harmonics-only (default: 8)')
    args = parser.parse_args()

    # Create output directory
    output_dir = "core/emd_analysis_output"
    os.makedirs(output_dir, exist_ok=True)

    if args.harmonics_only:
        run_harmonic_pairs_from_pickles(output_dir, args.n_workers)
        return

    print("Starting comprehensive EMD analysis...")

    # Load data
    mua_power_all_L4 = load_and_prepare_data()
    
    # Set sampling frequency
    fs = int(1 / (2 * 1e-3))  # 500 Hz
    
    print(f"Sampling frequency: {fs} Hz")
    print(f"Starting analysis for {len(mua_power_all_L4)} records...")
    
    # Perform EMD analysis for each trial and angle
    all_results = []
    
    with PdfPages(os.path.join(output_dir, 'emd_analysis_report.pdf')) as pdf:
        
        for idx, row in mua_power_all_L4.iterrows():
            trial_id = row['trial']
            angle = row['dir']
            mua_signal = row['mua']
            
            print(f"Processing trial {trial_id}, angle {angle}...")
            
            # Perform EMD analysis
            results = perform_emd_analysis(mua_signal, fs, trial_id, angle, output_dir)
            all_results.append(results)
            
            # Create and save figure
            fig = create_emd_figure(results, fs)
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        # Save all-pairs harmonic criteria across recordings
        pair_frames = []
        for r in all_results:
            if 'harmonic_criteria_all_pairs' in r:
                df_pairs = pd.DataFrame(r['harmonic_criteria_all_pairs'])
                df_pairs.insert(0, 'trial', r['trial'])
                df_pairs.insert(1, 'angle', r['angle'])
                pair_frames.append(df_pairs)
        if pair_frames:
            save_harmonic_pairs_table(pair_frames, output_dir)

        # Generate and save summary
        print("Generating summary statistics...")
        summary = generate_summary_statistics(all_results)
        
        # Save summary to JSON
        with open(os.path.join(output_dir, 'analysis_summary.json'), 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Create summary figure
        summary_fig = create_summary_figure(summary, all_results)
        pdf.savefig(summary_fig, bbox_inches='tight')
        plt.close(summary_fig)
        
        print(f"Analysis complete!")
        print(f"Results saved to: {output_dir}")
        print(f"PDF report: {os.path.join(output_dir, 'emd_analysis_report.pdf')}")
        print(f"Summary statistics: {os.path.join(output_dir, 'analysis_summary.json')}")
        print(f"\nSummary:")
        print(f"- Total analyses: {summary['total_analyses']}")
        print(f"- Successful: {summary['successful_analyses']}")
        print(f"- Failed: {summary['failed_analyses']}")
        print(f"- Unique trials: {summary['unique_trials']}")
        print(f"- Unique angles: {summary['unique_angles']}")

if __name__ == "__main__":
    main()