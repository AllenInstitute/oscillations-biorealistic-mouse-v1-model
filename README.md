# biorealistic-v1-model

A project for making biorealistic model of mouse V1.
This is a successor project of making a model of the mouse primary visual cortex
(<https://portal.brain-map.org/explore/models/mv1-all-layers>)

The improvements will be:

* Connection probability and weights are derived from coherent datasets, including the Allen Institute synaptic physiology data and MICrONS electron microscopy connectomics dataset (instead from the literature).
* Synaptic connections are now expressed by double alpha functions and the receptor types are more elaborated.
* Segregation of the L5 excitatory cells into IT, ET, and NP types.
* More GLIF cell models are used.

Only PointNet version is available as of now.

## Installation instruction

First, clone this repository to your local environment.

```bash
git clone https://github.com/AllenInstitute/biorealistic-v1-model.git
```

I suggest using [miniforge](https://github.com/conda-forge/miniforge) if you are setting up the environment for this. (Other conda variants will also work, if you specify 'conda-forge' as the primary package source.)

The 'conda' command can be replaced with 'mamba' if you have it installed, and it's much faster than 'conda'.

```bash
conda env create -f environment.yml -n <env_name>
```

## How to build a network and run a simulation

The most straightforward way to get a network and its simulation output is doing the following.

```bash
snakemake <network_name>/output_plain/spikes.h5
```

where `<network_name>` is one of the defined names in `Snakefile`. Namely:

* `full`: The full size network (700 µm radius, ~203k neurons)
* `core`: 400 µm radius network. ~67k neurons.
* `core_X`: X is {0-9}. The number of neurons in each cell model has Poisson fluctuation.
* `core_nll`: Same geometry as core, but no weight like-to-like is used.
* `core_nll_X`: Same as core_X, but no weight like-to-like is used.
* `small`: 200 µm radius network.
* `tiny`: 100 µm radius network. Mainly for testing the build script.
* `profile`: For profiling workflows. 200 µm radius.

You can create a custom size if you define parameters in `Snakefile`.

Also, you can edit `V1model_seed_file.xlsx` to change what cell types are be included. For example, if you want to make L4 only network, you can delete all the cell types other than L4 from this file.

Building the `full` model requires hundreds of GBs of memory. It usually needs to be run on a cluster computer, but it is not incorporated in the snakemake workflow yet. If you really need the `full` network, running the build script should be done manually. The subsequent processes should work fine once you build the model.

## Folders and files

base_props/: A folder that contains seed files that are necessary for building the network. These are mostly designed to be human readable and editable.

base_props/V1model_seed_file.xlsx: An excel file that contains general properties of
each cell population. Edit this when you want to change which cell population is used
and their numbers.

base_props/exclude_list.csv: Cells listed in this file will be excluded from the model. The reasons could vary, but generally due to undesired properties in the model, such as spiny inhibitory cells, aspiny excitatory cells, or that the model does not well reproduce cell's activity.

base_props/bkg_weights_population.csv: This file defines synaptic weights from background cell (currently, there is only one entity for background source) to each cell population. The synaptic weights in this file are copied from the previous model (except for L5 which is average of the two types in the previous model), and are parameters of the optimization stage later.

Preferred data storage option is CSV format, as long as the data are not large. All the csv files are 'space' separarated (to match with SONATA format). Larger data can be stored as h5 data frame. All should be readable in pandas.


## Notes
In the new V1 model, the LGN coordinates are defined as the visual field coordinates
(elevation and azimuth), though these coordinates are not zero-centered.
The LGN’s elevation axis is oriented upward, aligning with the V1 model’s z-axis;
however, this may conflict with conventional image coordinate systems, where row indices
increase downward. Note that this definition differs from our previous model (Billeh et
al., 2020), which defined the LGN coordinate axis as downward.
Use the y_dir and flip_y options in BMTK to control image orientation when presenting
data to this network.



## Snakemake pipeline targets

### Single-network targets

Any network can be targeted by its output file path. `{network_name}` is one of the names
defined in the Snakefile (see below for the full list). `{input_type}` is one of the
available network options (see below).

```bash
# Run simulation and produce spike output
snakemake {network_name}/output_{input_type}/spikes.h5

# Raster and spectra plot
snakemake {network_name}/output_{input_type}/raster_and_spectra_by_tuning_angle.png

# Contrast response plot
snakemake {network_name}/figures/contrast_responsive_cells_{input_type}.pdf

# OSI/DSI plot
snakemake {network_name}/figures/OSI_DSI_{input_type}.png
```

Available `input_type` values:
- `plain`, `adjusted`, `bio_trained`, `naive` — used for most analyses
- `plain`, `adjusted`, `bio_trained`, `naive`, `bio_free`, `uni_reg` — used for rasters

Available `{network_name}` values:
- `core_0` … `core_9` — 400 µm radius, Poisson-fluctuated neuron counts
- `core_nll_0` … `core_nll_9` — same, no weight like-to-like
- `core` — single 400 µm radius network
- `core_nll` — single 400 µm, no weight like-to-like
- `small` — 200 µm radius
- `full` / `full_nll` — 700 µm radius (requires cluster)
- `tiny` — 50 µm radius (testing)
- `profile` — 100 µm radius (profiling)

---

### Aggregate targets (baseline model)

These targets collect outputs across all 10 randomised core seeds.

```bash
# All simulations for core seeds (spikes only)
snakemake all_cores

# All raster plots for core seeds
snakemake all_cores_plot

# Rasters for all 10 core_nll seeds (adjusted only)
snakemake all_core_nlls_plot

# Contrast response plots — all input types
snakemake all_cores_nll_contrast_plot

# Contrast response plots — plain + adjusted only
snakemake all_cores_nll_contrast_plot_notf

# Raster plots — all input types
snakemake all_cores_nll_rasters

# Raster plots — plain + adjusted only
snakemake all_cores_nll_rasters_notf

# OSI/DSI plots — all input types
snakemake all_core_nll_odsi_plots

# OSI/DSI plots — plain + adjusted only
snakemake all_core_nll_odsi_plots_notf

# Response correlation plots + aggregated
snakemake all_cores_nll_response_corr_plot

# All response correlation plots (per-network + aggregated)
snakemake all_response_correlation_plots

# All analysis for core_nll_0 (contrast + raster + OSI/DSI + spectra)
snakemake all_core_nll_0_all

# Combo targets
snakemake all_cores_notf       # contrast + raster + OSI/DSI, plain+adjusted only
snakemake all_cores_all        # contrast + raster + OSI/DSI, all input types

# Sparsity
snakemake all_nll_sparsity           # lifetime + population sparsity, all seeds
snakemake plot_population_sparsity   # population sparsity plots
snakemake plot_lifetime_sparsity     # lifetime sparsity plots

# Spectral analysis
snakemake all_spectral_analysis      # compute spectra, all seeds
snakemake all_spectral_plots         # plot spectra, all seeds
snakemake aggregate_spectra          # aggregate across seeds
snakemake aggregate_spectra_normalized
snakemake all_spectral               # all of the above

# Background weight adjustment
snakemake bkg_adjustment

# Single-network convenience
snakemake all     # small/figures/OSI_DSI.png
snakemake core_spikes
```

---

### Running a single model variant

Pass `--config model_variant=<VARIANT>` to redirect all input files to
`base_props_<VARIANT>/` and prefix all output directories with `<VARIANT>_`.

```bash
snakemake --config model_variant=i4Pvalb-like-i4Sst all_cores
snakemake --config model_variant=L4-e2e-syn-as-L6 all_cores_all
snakemake --config model_variant=PV-like-Sst all_spectral
```

The first time a variant target is built, a symlink
`base_props → base_props_<VARIANT>` is created automatically so that scripts
using hard-coded `base_props/` paths read the correct variant files.

Available model variants:

| Variant name | Source directory |
|---|---|
| `i4Pvalb-like-i4Sst` | `base_props_i4Pvalb-like-i4Sst/` |
| `i4Sst-like-i4Pvalb` | `base_props_i4Sst-like-i4Pvalb/` |
| `L4-cell-density-as-L6` | `base_props_L4-cell-density-as-L6/` |
| `L4-cell-vol-dens-conn-as-L6` | `base_props_L4-cell-vol-dens-conn-as-L6/` |
| `L4-cell-volume-density-as-L6` | `base_props_L4-cell-volume-density-as-L6/` |
| `L4-connectivity-as-L6` | `base_props_L4-connectivity-as-L6/` |
| `L4-e2e-syn-as-L6` | `base_props_L4-e2e-syn-as-L6/` |
| `L4-e2i-syn-as-L6` | `base_props_L4-e2i-syn-as-L6/` |
| `L4-i2e-syn-as-L6` | `base_props_L4-i2e-syn-as-L6/` |
| `L4-Pvalb2e-as-L6` | `base_props_L4-Pvalb2e-as-L6/` |
| `L4-Pvalb2e-syn-lat-as-L6` | `base_props_L4-Pvalb2e-syn-lat-as-L6/` |
| `L4-Pvalb2e-syn-tau-amp-as-L6` | `base_props_L4-Pvalb2e-syn-tau-amp-as-L6/` |
| `L4-Sst2e-as-L6` | `base_props_L4-Sst2e-as-L6/` |
| `L4-Sst2e-syn-lat-as-L6` | `base_props_L4-Sst2e-syn-lat-as-L6/` |
| `L4-Sst2e-syn-tau-amp-as-L6` | `base_props_L4-Sst2e-syn-tau-amp-as-L6/` |
| `L4-syn-as-L6-syn` | `base_props_L4-syn-as-L6-syn/` |
| `L4-syn-PSP-as_L6` | `base_props_L4-syn-PSP-as_L6/` |
| `L4-syn-weights-as-L6` | `base_props_L4-syn-weights-as-L6/` |
| `L4-Vip2e-syn-lat-as-L6` | `base_props_L4-Vip2e-syn-lat-as-L6/` |
| `L4-Vip2e-syn-tau-amp-as-L6` | `base_props_L4-Vip2e-syn-tau-amp-as-L6/` |
| `L4-weights-as-L6` | `base_props_L4-weights-as-L6/` |
| `L6-as-L4` | `base_props_L6-as-L4/` |
| `L6-syn-as-L4-syn` | `base_props_L6-syn-as-L4-syn/` |
| `L6-syn-as-L4-syn-PSP` | `base_props_L6-syn-as-L4-syn-PSP/` |
| `L6-syn-as-L4-syn-v2` | `base_props_L6-syn-as-L4-syn-v2/` |
| `L6-syn-as-L4-syn-v3` | `base_props_L6-syn-as-L4-syn-v3/` |
| `PV-like-Sst` | `base_props_PV-like-Sst/` |
| `PV-syn-like-Sst-syn` | `base_props_PV-syn-like-Sst-syn/` |
| `Sst-like-PV` | `base_props_Sst-like-PV/` |

---

### Multi-variant aggregate targets

These rules collect outputs across **all 29 variants × 10 seeds**. Each variant's
outputs must be built first (see above) before these aggregate rules can find the files.

```bash
# Raster plots for every variant × seed × input_type
snakemake all_variants_cores_nll_rasters

# Contrast response plots for every variant × seed
snakemake all_variants_cores_nll_contrast_plots

# OSI/DSI plots for every variant × seed
snakemake all_variants_core_nll_odsi_plots

# Spike outputs for every variant × seed (plain + adjusted)
snakemake all_variants_cores_nll_spikes

# Spectral analysis for every variant × seed
snakemake all_variants_spectral_analysis

# All primary analyses across every variant
snakemake all_variants_all
```

---

### Utility targets

```bash
snakemake clean          # remove all generated outputs
snakemake graph          # produce workflow_graph.pdf via Graphviz
snakemake profile_build  # cProfile the build script
snakemake clear_logs     # delete job log files
```

---

## Main contributors

* Shinya Ito
* Darrell Haufler
* Kael Dai
