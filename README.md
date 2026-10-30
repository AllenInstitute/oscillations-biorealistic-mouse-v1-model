# oscillations-biorealistic-mouse-v1-model

Code for studying circuit and cell-type mechanisms of laminar oscillations in a biorealistic model of mouse primary visual cortex (V1).

The repository has two main folders: one builds, simulates and analyzes the V1
network, and the other trains its synaptic weights.

```
oscillations-biorealistic-mouse-v1-model/
├── biorealistic-mouse-v1-model/            # build the network, run simulations, analyze, make figures
└── biorealistic-mouse-v1-model-training/   # train the network weights with TensorFlow
```

## `biorealistic-mouse-v1-model/`

The V1 model (based on
[AllenInstitute/biorealistic-v1-model](https://github.com/AllenInstitute/biorealistic-v1-model))
and everything needed to reproduce the paper's simulations, analyses and figures:

- **Network building:** a Snakemake pipeline builds the baseline network (`core`)
  and the model variants (`core_<variant>`, e.g. `core_L6-as-L4`) in SONATA
  format from the cell-type and connectivity data in `base_props*/`.
- **Simulations:** scripts that generate SLURM job arrays and BMTK configs for
  the LGN (filternet) and V1 (PointNet/NEST) simulations: drifting gratings,
  contrasts, temporal frequencies, gray screen, natural scenes and movies, and
  optogenetic-like silencing of layers or inhibitory populations
  (`make_*jobs*.py`).
- **Analysis:** `analysis_*.py` scripts that compute laminar and cell-type MUA
  power spectra into each network's `metrics/` folder, plus the EMD analysis of
  L4 activity (`emd_analysis_comprehensive.py`).
- **Figures:** `fig*.ipynb` notebooks that generate the manuscript figures into
  `paper_figs/`.

Use the `osc-mouse-v1-model` conda environment (`environment.yml`). See
[biorealistic-mouse-v1-model/README.md](biorealistic-mouse-v1-model/README.md)
for installation, network building, simulations and the analysis-to-figure map,
and [README_V1_model.md](biorealistic-mouse-v1-model/README_V1_model.md) for
the original model description.

## `biorealistic-mouse-v1-model-training/`

A TensorFlow implementation of the same V1 network with GLIF neurons and
double-alpha synapses (based on
[JavierGalvan9/V1_GLIF_model](https://github.com/JavierGalvan9/V1_GLIF_model)).
It is used to train the recurrent and background weights
so the network matches experimental firing rates and orientation/direction
selectivity (Neuropixels data):

- `parallel_training_testing*.py` and `multi_training*.py` run the training;
  `--data_dir GLIF_network_<variant>` selects the network and
  `--synaptic_data_dir synaptic_data_<variant>` its synaptic basis data.
- `v1_model_utils/checkpoint_to_edges.py` writes the trained weights back into
  SONATA edge files.
- `osi_dsi_estimator.py` and `osi_dsi_analysis.ipynb` evaluate the trained
  model's tuning.

Use the `tf215` conda environment (`biorealistic-mouse-v1-model-training/environment.yml`).
See [biorealistic-mouse-v1-model-training/README.md](biorealistic-mouse-v1-model-training/README.md)
for details.

## How the two folders connect

1. Build a network in `biorealistic-mouse-v1-model/` (`core` or `core_<variant>`).
2. Copy it into the training folder:
   `biorealistic-mouse-v1-model-training/copy_glif_network.sh` (`core/network` →
   `GLIF_network`, `core_<variant>/network` → `GLIF_network_<variant>`).
3. Train the weights in `biorealistic-mouse-v1-model-training/` and convert the checkpoint
   to edge files with `checkpoint_to_edges.py`.
4. Copy the trained edge files back:
   `biorealistic-mouse-v1-model-training/copy_checkpoint_weights.sh` (→
   `core*/network/*_checkpoint.h5`).
5. Run the simulations, analyses and figure notebooks in
   `biorealistic-mouse-v1-model/` with the trained (`checkpoint`) weights, which
   were used for all the paper's analyses.

## Data

Large outputs (networks, simulation results, metrics, training checkpoints) are
not tracked in git; each folder's `.gitignore` lists them. The networks,
simulation results, metrics and training checkpoints used for the paper can be
accessed and downloaded from
[Dropbox](https://www.dropbox.com/scl/fo/xzcmw1tnkh1kv3kvo4ma4/AAZv3zGDzned--6RMw8bSQQ?rlkey=tr4gkoy6lomha00qiqjrgmrra&st=5ekwfoer&dl=0).
To run the analyses or figure notebooks, copy the downloaded folders into
`biorealistic-mouse-v1-model/`.
