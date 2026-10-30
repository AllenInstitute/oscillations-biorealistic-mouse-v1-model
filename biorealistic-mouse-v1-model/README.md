# Oscillations paper — reproducing simulations and analysis

A biorealistic model of mouse V1, used here to study gamma and alpha-beta
oscillations and their laminar organization. This folder is based on
[AllenInstitute/biorealistic-v1-model](https://github.com/AllenInstitute/biorealistic-v1-model)
and has been modified for our study of network oscillations.

The underlying V1 model is described in:

> Ito S., Haufler D., Galván Fraile J., Dai K., Aman J., Chen G., Mirasso C.,
> Maass W., Arkhipov A. (2026). *Deep-learning-assisted simulation of a cortical
> circuit: integrating anatomy, physiology and function.*
> bioRxiv. <https://doi.org/10.64898/2026.03.13.711751>

This is a successor of the mouse primary visual cortex model
(<https://portal.brain-map.org/explore/models/mv1-all-layers>), with the following
key improvements:

* Connection probability and weights derived from coherent datasets, including the
  Allen Institute synaptic physiology data and MICrONS electron microscopy
  connectomics dataset (instead of from the literature).
* Synaptic connections expressed by double alpha functions with more elaborated
  receptor types.
* Segregation of L5 excitatory cells into IT, ET, and NP types.
* More GLIF cell models.

Only PointNet simulations were used for the oscillations paper.

For a full description of the build pipeline used in the original study, network architecture, and Snakemake
targets see [README_V1_model.md](README_V1_model.md).

---

## Installation

First, clone the repository and move into this folder:

```bash
git clone https://github.com/AllenInstitute/oscillations-biorealistic-mouse-v1-model.git
cd oscillations-biorealistic-mouse-v1-model/biorealistic-mouse-v1-model
```

Create the conda environment (use [miniforge](https://github.com/conda-forge/miniforge)
or any conda variant with `conda-forge` as the primary channel; `mamba` is faster):

```bash
conda env create -f environment.yml   # creates the osc-mouse-v1-model environment
conda activate osc-mouse-v1-model
```

This single environment runs everything in this repository: network building
(Snakemake), filternet and PointNet (NEST 3.8) simulations, the analysis scripts
and the figure notebooks.

---

## Data

The networks, simulation results, metrics and training checkpoints used for the
paper are not tracked in git. They can be accessed and downloaded from
[Dropbox](https://www.dropbox.com/scl/fo/xzcmw1tnkh1kv3kvo4ma4/AAZv3zGDzned--6RMw8bSQQ?rlkey=tr4gkoy6lomha00qiqjrgmrra&st=5ekwfoer&dl=0).
To run the analyses or figure notebooks, copy the downloaded folders into this
folder (`biorealistic-mouse-v1-model/`).

---

## How to build a network

```bash
snakemake <network_name>/output_plain/spikes.h5
```

Available `<network_name>` values:

| Network name | Description |
|---|---|
| `full` | 700 µm radius (~203 k neurons) — requires cluster |
| `core` | 400 µm radius (~67 k neurons) |
| `core_X` (X = 0–9) | Same as `core` with Poisson-fluctuated neuron counts |
| `core_nll` | Same as `core`, no weight like-to-like |
| `core_nll_X` | Same as `core_X`, no weight like-to-like |
| `small` | 200 µm radius |
| `tiny` | 50 µm radius — for testing |
| `profile` | 100 µm radius — for profiling |

Edit `base_props_default/V1model_seed_file.xlsx` to control which cell types are
included. Building `full` requires hundreds of GB of RAM and must be run on a
cluster; subsequent Snakemake steps work normally once the network is built.

> **Note:** All simulations in our oscillations study use the **`core` network**
> (400 µm radius, ~67 k neurons). This is the network version built, trained, and
> analysed throughout the paper.

---

## Key directories and files

**`base_props/`** — seed files needed to build the network (human-readable CSV/XLSX).
`base_props` is a git-ignored *managed symlink* pointed at the active source directory
by the Snakefile: `base_props_default/` for the default build, or
`base_props_<VARIANT>/` when `--config model_variant=<VARIANT>` is set.

**`base_props/V1model_seed_file.xlsx`** — cell population properties (types and counts).

**`base_props/exclude_list.csv`** — cells excluded from the model.

**`base_props/bkg_weights_population.csv`** — synaptic weights from the background
source to each cell population; starting parameters for the optimization stage.

Data are stored as space-separated CSV (SONATA format) or HDF5 for larger files;
all are readable with pandas.

---

## Notes

LGN coordinates are defined in visual field coordinates (elevation and azimuth),
not zero-centered. The elevation axis is oriented upward (aligning with the V1
model's z-axis), which may conflict with image coordinate systems where row indices
increase downward. This differs from Billeh et al. (2020), which defined the axis
downward. Use the `y_dir` and `flip_y` options in BMTK to control image orientation.

---

## Getting the core network

Build the baseline `core` network and run a simulation:

```bash
# Build network, run simulation with plain (no TF-trained) weights
snakemake core/output_plain/spikes.h5

# With TF-trained (checkpoint) weights — used for all oscillations-paper analyses
snakemake core/output_checkpoint/spikes.h5
```

The `checkpoint` network option uses TF-trained synaptic weights from
`biorealistic-mouse-v1-model-training/`. All oscillations-paper simulations use this option.

---

## Running model variants

Each model variant modifies a subset of synaptic or structural properties relative
to the baseline `core`. Variants are defined by their `base_props_<VARIANT>/`
directory and are activated by passing `--config model_variant=<VARIANT>` to
Snakemake.

### Running a single variant

```bash
# Spikes for one variant
snakemake core_L4-Sst2e-as-L6/output_plain/spikes.h5 --config model_variant=L4-Sst2e-as-L6

# Any single-network target works the same way
snakemake core_0_L4-Sst2e-as-L6/output_adjusted/raster_and_spectra_by_tuning_angle.png \
    --config model_variant=L4-Sst2e-as-L6
snakemake core_PV-like-Sst/figures/OSI_DSI_plain.png --config model_variant=PV-like-Sst
```

> **CLI gotcha:** `--config` greedily consumes everything after it as `key=value`
> pairs, so **put the target *before* `--config`** (as above), or separate with `--`:
> ```bash
> snakemake --config model_variant=L4-Sst2e-as-L6 -- core_L4-Sst2e-as-L6/output_plain/spikes.h5
> ```

**How the variant redirect works.** The default props live in `base_props_default/`;
`base_props` is a git-ignored *managed symlink*. On every invocation the Snakefile
points `base_props` at the active source directory, so scripts that read hard-coded
`base_props/…` paths pick up the correct files automatically. Only one variant's
`base_props` can be active at a time — build each variant in its own `snakemake`
invocation.

**TF-training synaptic properties.** Because some variants have different synaptic
properties, TF-training outputs are written to `tf_props_<VARIANT>/` (the scripts
honor `$TF_PROPS_DIR`, set automatically by the Snakefile):

```bash
snakemake tf_props_L4-Sst2e-as-L6/basis_function_weights.csv \
    --config model_variant=L4-Sst2e-as-L6
```

### Building several variants sequentially (sweep script)

```bash
conda activate osc-mouse-v1-model
./build_selected_variant_core_spikes.sh          # default core seeds (8 cores)
./build_selected_variant_core_spikes.sh --cores 16
./build_selected_variant_core_spikes.sh --rerun-incomplete
```

Edit the `VARIANTS` list inside the script to choose which variants to build.
Re-running is safe — already-built variants are skipped.

### Multi-variant aggregate targets

These rules collect outputs across all 29 variants × 10 seeds. Each variant must be
built before these aggregate targets can find its files.

```bash
snakemake all_variants_cores_nll_rasters         # raster plots, all variants × seeds × input_type
snakemake all_variants_cores_nll_contrast_plots  # contrast response plots
snakemake all_variants_core_nll_odsi_plots       # OSI/DSI plots
snakemake all_variants_cores_nll_spikes          # spike outputs (plain + adjusted)
snakemake all_variants_spectral_analysis         # spectral analysis
snakemake all_variants_all                       # all primary analyses
```

### Available model variants

| Variant name | What is changed |
|---|---|
| `i4Pvalb-like-i4Sst` | L4 Pvalb cells receive L4 Sst-like inputs |
| `i4Sst-like-i4Pvalb` | L4 Sst cells receive L4 Pvalb-like inputs |
| `L4-cell-density-as-L6` | L4 cell density set to L6 values |
| `L4-cell-vol-dens-conn-as-L6` | L4 cell volume density and connectivity as L6 |
| `L4-cell-volume-density-as-L6` | L4 cell volume density as L6 |
| `L4-connectivity-as-L6` | L4 connectivity as L6 |
| `L4-e2e-syn-as-L6` | L4 E→E synaptic properties as L6 |
| `L4-e2i-syn-as-L6` | L4 E→I synaptic properties as L6 |
| `L4-i2e-syn-as-L6` | L4 I→E synaptic properties as L6 |
| `L4-Pvalb2e-as-L6` | L4 Pvalb→E synaptic properties as L6 |
| `L4-Pvalb2e-syn-lat-as-L6` | L4 Pvalb→E synaptic latency as L6 |
| `L4-Pvalb2e-syn-tau-amp-as-L6` | L4 Pvalb→E synaptic tau and amplitude as L6 |
| `L4-Sst2e-as-L6` | L4 Sst→E synaptic properties as L6 |
| `L4-Sst2e-syn-lat-as-L6` | L4 Sst→E synaptic latency as L6 |
| `L4-Sst2e-syn-tau-amp-as-L6` | L4 Sst→E synaptic tau and amplitude as L6 |
| `L4-syn-as-L6-syn` | All L4 synaptic properties as L6 |
| `L4-syn-PSP-as_L6` | L4 synaptic PSP amplitude as L6 |
| `L4-syn-weights-as-L6` | L4 synaptic weights as L6 |
| `L4-Vip2e-syn-lat-as-L6` | L4 Vip→E synaptic latency as L6 |
| `L4-Vip2e-syn-tau-amp-as-L6` | L4 Vip→E synaptic tau and amplitude as L6 |
| `L4-weights-as-L6` | L4 connection weights as L6 |
| `L6-as-L4` | L6 cells replaced with L4 models |
| `L6-syn-as-L4-syn` | L6 synaptic properties as L4 |
| `L6-syn-as-L4-syn-PSP` | L6 synaptic PSP as L4 |
| `L6-syn-as-L4-syn-v2` | L6 synaptic properties as L4 (v2) |
| `L6-syn-as-L4-syn-v3` | L6 synaptic properties as L4 (v3) |
| `PV-like-Sst` | PV cells given Sst-like properties |
| `PV-syn-like-Sst-syn` | PV synaptic properties as Sst |
| `Sst-like-PV` | Sst cells given PV-like properties |

---

## Simulation job scripts

Job-generation scripts live in the model root and write SLURM batch scripts +
per-trial JSON config files into `<network>/jobs/` and `<network>/configs/`.

All scripts default `--core_dir` to `<model_root>/core` so that model variant
networks reuse the filternet (LGN spike) and background (bkg) outputs already
computed for the baseline `core` network. Pass `--core_dir <path>` to override.

All main-simulation configs are written with `--dt 0.1` (ms) by default, which
overrides the `run.dt` of the base config (`config_templates/` use 0.25). Every
simulation in the paper, for the baseline and all model variants, used `dt = 0.1`.

> **Note:** These scripts are run directly (not via Snakemake). Snakemake handles
> network building and single-direction simulations; these scripts generate configs
> for the 8-direction × 10-trial SLURM array jobs and other multi-condition sweeps.

### Drifting gratings — 8 directions × 10 trials

```bash
# Generate SLURM job + per-trial configs for a variant network
python make_filternet_jobs.py core_L4-e2e-syn-as-L6 --network_option checkpoint

# Override filternet source (defaults to ./core)
python make_filternet_jobs.py core_L4-e2e-syn-as-L6 --network_option checkpoint \
    --core_dir /path/to/other/core

# Generate filternet configs (outputs to <network>/filternet_8dir_10trials/)
python make_filternet_jobs.py core --filternet
```

### Contrast response

```bash
# Standard contrast sweep (-> contrasts_checkpoint; 8 dir x 6 contrasts x 10 trials = 480 configs)
python make_contrast_jobs.py core --network_option checkpoint
python make_contrast_jobs.py core --filternet
```

Blank (contrast 0) trials are skipped by default; see
`stimulus_trials.ContrastStimulus(include_blanks=...)`.

### Temporal frequency tuning

```bash
# -> temporal_f_checkpoint; 8 dir x 6 TFs (1, 2, 4, 8, 15, 30 Hz) x 10 trials
python make_temporal_f_jobs.py core --network_option checkpoint
python make_temporal_f_jobs.py core --filternet
```

### All 8 directions in one 30 s run (Fig. 1B raster)

The LGN and background inputs are the 8 single-direction runs concatenated in
time; build them first with `concat_dg_lgn_inputs.ipynb` and
`concat_dg_bkg_inputs.ipynb`.

```bash
# -> all8dir_10trials_checkpoint (one config per trial)
python make_dir_jobs_alldirs.py core --network_option checkpoint
```

### Contrast response — temporal frequency 2 Hz

```bash
python make_contrast_jobs_tf2Hz.py core --network_option plain
python make_contrast_jobs_tf2Hz.py core --filternet
```

### Gray screen (spontaneous activity)

```bash
python make_filternet_jobs_gray_screen.py core --network_option checkpoint
python make_filternet_jobs_gray_screen.py core --filternet
```

### Natural movies

```bash
python make_filternet_jobs_natural_movies.py core natural_movie_one --network_option checkpoint
python make_filternet_jobs_natural_movies.py core natural_movie_two --network_option checkpoint
```

### Natural scenes

```bash
python make_filternet_jobs_natural_scenes.py core --network_option checkpoint
```

### Optogenetic silencing — population

```bash
python make_filternet_jobs_opto_pop_silencing.py core --perturb_pop Pvalb --percentage 100
python make_filternet_jobs_opto_pop_silencing.py core --perturb_pop Sst   --percentage 100
python make_filternet_jobs_opto_pop_silencing.py core --perturb_pop Vip   --percentage 100
```

### Optogenetic silencing — layer

```bash
python make_filternet_jobs_opto_layer_scilencing.py core --perturb_layer L4
python make_filternet_jobs_opto_layer_scilencing.py core --perturb_layer L1 L23 L5 L6
# L4-only variant:
python make_filternet_jobs_opto_layer_scilencing_L4.py core --perturb_pop i4Sst
```

For both population-silencing scripts, the silenced cells are drawn from
`<basedir>/network/` (or `network_<network_folder>/`), and `--percentage` is
used verbatim in folder names (e.g. `--percentage 75.0` -> `..._75.0perc_checkpoint`).

Below 100 %, a different random subset of cells is silenced in each config
(each angle × trial). The subsets are drawn with `--seed` (default 0), so
rerunning a script gives the same cells. The published L4-only partial-silencing
simulations predate the seed, so their exact cell lists are stored in
`silencing_node_ids/` (one JSON per run, `node_ids[i]` = cells silenced in
`config_<i>`). Pass one with `--node_ids_file` to reproduce a run exactly:

```bash
python make_filternet_jobs_opto_layer_scilencing_L4.py core --perturb_pop i4Pvalb --percentage 10 \
    --node_ids_file silencing_node_ids/8dir_10trials_onlyL4_-2000_silencing_i4Pvalb_10perc_checkpoint.json
```

---

## Completed simulations

All outputs live under `<model_dir>/core/` for each model variant directory.
`checkpoint` = TF-trained synaptic weights.

### Baseline model (`biorealistic-v1-model/core`)

| Simulation type | Output directory |
|---|---|
| Drifting gratings (8 dir × 10 trials) | `8dir_10trials_checkpoint` |
| Temporal frequency tuning | `temporal_f_checkpoint` |
| Contrast response (standard) | `contrasts_checkpoint` |
| Gray screen / spontaneous | `3s_gs_10trials_checkpoint` |
| Natural movie one | `natural_movie_one_10trials_checkpoint` |
| Natural movie two | `natural_movie_two_10trials_checkpoint` |
| Natural scenes | `natural_scenes_10trials_checkpoint` |
| L4 with L6 models | `8dir_10trials_L4_with_L6_models_checkpoint` |
| Population silencing — per layer (i23/i4/i5/i6 × Pvalb/Sst/Vip, 100 %) | `8dir_10trials_-2000_silencing_<pop>_100perc_checkpoint` |
| Population silencing — whole cortex (Pvalb/Sst/Vip, 100 %) | `8dir_10trials_-2000_silencing_{Pvalb,Sst,Vip}_100perc_checkpoint` |
| L4-only population silencing (Pvalb/Sst/Vip, 10–100 %) | `8dir_10trials_onlyL4_-2000_silencing_i4{Pvalb,Sst,Vip}_{perc}_checkpoint` |
| Layer silencing — individual layers (L1, L23, L4, L5, L6) | `8dir_10trials_opto_layer_silencing_<layer>_-2000_checkpoint` |
| Layer silencing — pairs and triples | `8dir_10trials_opto_layer_silencing_<layers>_-2000_checkpoint` |
| L4 with L6 models + layer silencing | `8dir_10trials_L4_with_L6_models_opto_layer_silencing_*_checkpoint` |

### Model variants — completed simulations

All variants share the baseline `core` filternet / LGN inputs. Each ran:

| Simulation | Output directory |
|---|---|
| Drifting gratings (8 dir × 10 trials) | `8dir_10trials_checkpoint` |
| Layer silencing L1+L23+L5+L6 | `8dir_10trials_opto_layer_silencing_L1_L23_L5_L6_-2000_checkpoint` |

Variants with these outputs:
`i4Pvalb-like-i4Sst`, `i4Sst-like-i4Pvalb`, `L4-cell-vol-dens-conn-as-L6`,
`L4-cell-volume-density-as-L6`, `L4-connectivity-as-L6`, `L4-e2e-syn-as-L6`,
`L4-e2i-syn-as-L6`, `L4-i2e-syn-as-L6`, `L4-Pvalb2e-as-L6`,
`L4-Pvalb2e-syn-lat-as-L6`, `L4-Pvalb2e-syn-tau-amp-as-L6`, `L4-Sst2e-as-L6`,
`L4-Sst2e-syn-lat-as-L6`, `L4-Sst2e-syn-tau-amp-as-L6`, `L4-syn-as-L6-syn`,
`L4-syn-PSP-as_L6`, `L4-Vip2e-syn-lat-as-L6`, `L4-Vip2e-syn-tau-amp-as-L6`.

Additional simulations for selected variants:

**`L6-as-L4`** — `8dir_10trials_L6_with_L4_models_checkpoint`, layer silencing
L1+L23+L4+L5 and L1+L23+L5+L6, LGN→L6 weight perturbations ×2/×5/×10.

**`L6-syn-as-L4-syn`** — layer silencing L1+L23+L4+L5 and L1+L23+L5+L6, LGN→L6
weight perturbations ×2/×5/×10/×20 each with and without silencing.

**`L6-syn-as-L4-syn-v2`** — layer silencing L1+L23+L4+L5 and L1+L23+L5+L6.

**`PV-like-Sst`** — layer silencing L1+L23+L5+L6 only (no baseline 8dir run).

---

## Analysis scripts

Each analysis script reads the spike outputs of `<net_name>` (default `core`;
pass `--net_name core_<variant>` for a model variant) and writes per-population
and per-layer MUA power spectra (`.csv` + `.pkl`) to
`<net_name>/metrics/<folder>/`. The figure notebooks read those files.

| Script | Output folder (`<net_name>/metrics/`) | Used by |
|---|---|---|
| `analysis_dg_layer_power.py` | `dg_power` | `fig1C_dg_power.ipynb` |
| `analysis_dg_contrasts_power.py` | `dg_contrasts_power` | `fig1_suppl_dg_power_contrasts.ipynb` |
| `analysis_dg_temporal_f_power.py` | `dg_temporal_f_power` | `fig1_suppl_dg_power_temporal_fs.ipynb` |
| `analysis_gray_screen_vs_dg_power.py` | `gray_screen_vs_dg_power` | `fig1_suppl_gs_power.ipynb` |
| `analysis_lgn_unit_power.py` | `lgn_unit_power` | `fig1_suppl_lgn_unit_power_spectrum.ipynb` |
| `emd_analysis_comprehensive.py` | `core/emd_analysis_output` | `fig1_suppl2_emd_summary_figures.ipynb` |
| `analysis_natural_stim_power.py` | `other_visual_stim_power` | `fig2C_dg_power_naturalistic_stim_v2.ipynb` |
| `analysis_dg_inh_pop_silencing_power.py` | `dg_inh_pop_silencing_power` | `fig3_dg_power_inh_pop_silencing.ipynb` |
| `analysis_dg_layer_silencing_power.py` | `dg_layer_silencing_power` | `fig4_dg_power_layers_silencing.ipynb` |
| `analysis_dg_L4_inh_silencing_power.py` | `dg_L4_inh_silencing_power` | `fig4_dg_power_layers_silencing.ipynb` |
| `analysis_dg_L4L6model_silencing_power.py` | `dg_L4L6model_silencing_power` | `fig5_dg_power_net_pertb.ipynb` |
| `analysis_dg_layer_silencing_power_L4_model_variants.py` | `dg_layer_silencing_power` (in `core_<variant>`) | `fig5_dg_power_net_pertb.ipynb` |
| `analysis_dg_layer_silencing_power_L6_model_variants.py` | `dg_layer_silencing_power` (in `core_<variant>`) | `fig5_dg_power_net_pertb.ipynb` |

`emd_analysis_comprehensive.py` is an empirical mode decomposition (EMD) of the
L4 MUA with all other layers silenced (condition `L4`, 8 directions × 10 trials;
see `emd_analysis_methods.md`).

The raster notebooks (`fig1B`, `fig2CD`, `fig2_suppl`, `fig3A`, `fig4A`,
`fig4_suppl`, `fig5_suppl`) read spike outputs directly. `fig1B` uses the 30 s
all-direction runs (`all8dir_10trials_checkpoint`, see below).

---

## Main contributors

* Beatriz Herrera
* Shinya Ito
* Darrell Haufler
* Kael Dai
