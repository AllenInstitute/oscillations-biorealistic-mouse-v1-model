# biorealistic-v1-model — model description and build pipeline

A biorealistic model of mouse V1. If you use this model, please cite:

> Ito S., Haufler D., Galván Fraile J., Dai K., Aman J., Chen G., Mirasso C.,
> Maass W., Arkhipov A. (2026). *Deep-learning-assisted simulation of a cortical
> circuit: integrating anatomy, physiology and function.*
> bioRxiv. <https://doi.org/10.64898/2026.03.13.711751>

This is a successor project of the mouse primary visual cortex model
(<https://portal.brain-map.org/explore/models/mv1-all-layers>).

The improvements are:

* Connection probability and weights derived from coherent datasets, including the
  Allen Institute synaptic physiology data and MICrONS electron microscopy
  connectomics dataset (instead of from the literature).
* Synaptic connections expressed by double alpha functions with more elaborated
  receptor types.
* Segregation of L5 excitatory cells into IT, ET, and NP types.
* More GLIF cell models.

Only PointNet version is available as of now.

---

## Installation

First, clone the repository:

```bash
git clone https://github.com/AllenInstitute/biorealistic-v1-model.git
```

Create the conda environment (use [miniforge](https://github.com/conda-forge/miniforge)
or any conda variant with `conda-forge` as the primary channel; `mamba` is faster):

```bash
conda env create -f environment.yml -n <env_name>
```

---

## How to build a network and run a simulation

The most straightforward way to get a network and its simulation output:

```bash
snakemake <network_name>/output_plain/spikes.h5
```

where `<network_name>` is one of the defined names in `Snakefile`:

| Network name | Description |
|---|---|
| `full` | Full size, 700 µm radius (~203 k neurons) — requires cluster |
| `core` | 400 µm radius (~67 k neurons) |
| `core_X` (X = 0–9) | Same as `core` with Poisson-fluctuated neuron counts |
| `core_nll` | Same as `core`, no weight like-to-like |
| `core_nll_X` | Same as `core_X`, no weight like-to-like |
| `small` | 200 µm radius |
| `tiny` | 50 µm radius — for testing the build script |
| `profile` | 100 µm radius — for profiling |

You can define custom sizes by adding parameters to `Snakefile`.

You can also edit `base_props_default/V1model_seed_file.xlsx` to control which cell
types are included (e.g. delete all non-L4 rows to build an L4-only network).

Building `full` requires hundreds of GB of RAM and must be run on a cluster
computer; the subsequent Snakemake steps work normally once the network is built.

---

## Folders and files

**`base_props/`** — seed files needed to build the network; mostly human-readable
and editable CSV/XLSX. Note: `base_props` itself is a git-ignored *managed
symlink* automatically pointed at the active source directory by the Snakefile:
`base_props_default/` for the default build, or `base_props_<VARIANT>/` when
`--config model_variant=<VARIANT>` is set. To edit the default seed files, edit
them in `base_props_default/`.

**`base_props/V1model_seed_file.xlsx`** — general properties of each cell
population (which populations are included and their counts).

**`base_props/exclude_list.csv`** — cells excluded from the model (e.g. spiny
inhibitory cells, aspiny excitatory cells, or models that do not well reproduce
cell activity).

**`base_props/bkg_weights_population.csv`** — synaptic weights from the background
source to each cell population. Copied from the previous model for L5 (averaged
across types) and used as starting parameters for the optimization stage.

Preferred data storage format is CSV (space-separated, to match SONATA format).
Larger data are stored as HDF5. All files are readable with pandas.

---

## Notes

In the new V1 model, LGN coordinates are defined in visual field coordinates
(elevation and azimuth), not zero-centered. The elevation axis is oriented upward,
aligning with the V1 model's z-axis; this may conflict with conventional image
coordinate systems where row indices increase downward. This differs from the
previous model (Billeh et al., 2020), which defined the elevation axis downward.

Use the `y_dir` and `flip_y` options in BMTK to control image orientation when
presenting stimuli to this network.

---

## Snakemake pipeline targets

### Single-network targets

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
- `plain`, `adjusted`, `bio_trained`, `naive` — most analyses
- `plain`, `adjusted`, `bio_trained`, `naive`, `bio_free`, `uni_reg` — rasters

---

### Aggregate targets (baseline model)

```bash
snakemake all_cores                      # spikes for all 10 core seeds
snakemake all_cores_plot                 # raster plots for all 10 core seeds
snakemake all_core_nlls_plot             # rasters for all 10 core_nll seeds (adjusted only)
snakemake all_cores_nll_contrast_plot    # contrast response plots — all input types
snakemake all_cores_nll_contrast_plot_notf  # contrast response — plain + adjusted only
snakemake all_cores_nll_rasters          # raster plots — all input types
snakemake all_cores_nll_rasters_notf     # raster plots — plain + adjusted only
snakemake all_core_nll_odsi_plots        # OSI/DSI — all input types
snakemake all_core_nll_odsi_plots_notf   # OSI/DSI — plain + adjusted only
snakemake all_cores_nll_response_corr_plot  # response correlation plots + aggregated
snakemake all_response_correlation_plots    # per-network + aggregated response correlation
snakemake all_core_nll_0_all             # all analysis for core_nll_0
snakemake all_cores_notf                 # contrast + raster + OSI/DSI, plain+adjusted only
snakemake all_cores_all                  # contrast + raster + OSI/DSI, all input types
snakemake all_nll_sparsity               # lifetime + population sparsity, all seeds
snakemake plot_population_sparsity       # population sparsity plots
snakemake plot_lifetime_sparsity         # lifetime sparsity plots
snakemake all_spectral_analysis          # compute spectra, all seeds
snakemake all_spectral_plots             # plot spectra, all seeds
snakemake aggregate_spectra              # aggregate across seeds
snakemake aggregate_spectra_normalized
snakemake all_spectral                   # all spectral targets
snakemake bkg_adjustment                 # background weight adjustment
snakemake all                            # small/figures/OSI_DSI.png
snakemake core_spikes                    # core spike output only
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
