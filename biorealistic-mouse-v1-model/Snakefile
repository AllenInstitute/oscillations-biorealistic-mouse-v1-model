import os
import re
import sys

main_scripts = ["build_network.py", "edge_funcs.py", "node_funcs.py"]

# ============================================================
# Model variants
# Each corresponds to a biorealistic-v1-model-<suffix> directory
# whose base_props/ has been copied here as base_props_<suffix>/
# ============================================================
model_variants = [
    "i4Pvalb-like-i4Sst",
    "i4Sst-like-i4Pvalb",
    # "L4-cell-density-as-L6",
    "L4-cell-vol-dens-conn-as-L6",
    "L4-cell-volume-density-as-L6",
    "L4-connectivity-as-L6",
    "L4-e2e-syn-as-L6",
    "L4-e2i-syn-as-L6",
    "L4-i2e-syn-as-L6",
    "L4-Pvalb2e-as-L6",
    "L4-Pvalb2e-syn-lat-as-L6",
    "L4-Pvalb2e-syn-tau-amp-as-L6",
    "L4-Sst2e-as-L6",
    "L4-Sst2e-syn-lat-as-L6",
    "L4-Sst2e-syn-tau-amp-as-L6",
    "L4-syn-as-L6-syn",
    "L4-syn-PSP-as_L6",
    "L4-Vip2e-syn-lat-as-L6",
    "L4-Vip2e-syn-tau-amp-as-L6",
    "L6-as-L4",
    "L6-syn-as-L4-syn",
    "L6-syn-as-L4-syn-PSP",
    "PV-like-Sst",
    "PV-syn-like-Sst-syn",
    "Sst-like-PV",
]

# ============================================================
# Variant configuration  (set via --config model_variant=NAME)
#   snakemake --config model_variant=i4Pvalb-like-i4Sst all_cores
# Leave unset (or empty string) to use the default (base_props_default/).
#
# The default props now live in base_props_default/; `base_props` is a
# managed symlink (git-ignored) that points at the active source dir.
# Many scripts read hard-coded "base_props/..." paths, so the symlink must
# always resolve to the props for the active variant (or the default).
# ============================================================
model_variant = config.get("model_variant", "")
_variant_slug = model_variant if model_variant else "default"
# Physical source directory holding the active props.
base_props_dir = f"base_props_{model_variant}" if model_variant else "base_props_default"
vs = f"_{model_variant}" if model_variant else ""   # suffix for all variant output dirs: <network>_<variant>
# Every build depends on the base_props symlink being pointed at base_props_dir.
setup_deps = [f".base_props_{_variant_slug}_setup"]
# TF-training synaptic-property outputs go to a per-variant dir so variants with
# different synaptic properties don't clobber each other: tf_props_<variant>
# (plain tf_props for the default). The tf scripts read this via $TF_PROPS_DIR.
tf_props_dir = "tf_props" + vs


# ------------------------------------------------------------
# Point the managed `base_props` symlink at the active source dir *now*,
# before any rule runs. This guarantees correctness even for analysis-only
# targets whose upstream build outputs are already cached (and therefore
# would not otherwise trigger the setup_base_props rule below).
# Safe: it never clobbers a real directory (see legacy warning).
# ------------------------------------------------------------
if os.path.isdir(base_props_dir):
    if os.path.islink("base_props"):
        if os.readlink("base_props") != base_props_dir:
            os.remove("base_props")
            os.symlink(base_props_dir, "base_props")
    elif not os.path.exists("base_props"):
        os.symlink(base_props_dir, "base_props")
    else:
        sys.stderr.write(
            "WARNING: 'base_props' exists but is not a managed symlink; "
            "variant redirection is disabled. Move it to 'base_props_default' "
            "and delete 'base_props' to enable variant builds.\n"
        )


# ============================================================
# Build-phase input files (parameterised by active variant)
# ============================================================
build_files = [
    f"{base_props_dir}/lgn_weights_population.csv",
    f"{base_props_dir}/lgn_params.csv",
    f"{base_props_dir}/lgn_models.csv",
    "glif_props/v1_node_models.csv",
    "glif_props/v1_edge_models.csv",
    "glif_props/lgn_weights_model.csv",
    "glif_props/bkg_weights_model.csv",
    "glif_models/cell_models/313861608_glif_lif_asc_config.json"  # representative
]

config_files = [
    "config_adjusted.json",
    "config_bkg.json",
    "config_lgn.json",
    "config_lgnbkg.json",
    "config_plain.json",
    "config_checkpoint.json",
    "config_noweightloss.json",
    "config_bio_trained.json",
    "config_bio_free.json",
    "config_uni_reg.json",
    "config_naive.json",
    "config_bkgtune.json",
    "config_filternet.json",
    "config_filternet_bkgtune.json",
    "config_multimeter.json",
]

# available network options
network_options = [
    "plain",
    "adjusted",
    "checkpoint",
    "noweightloss",
    "bio_trained",
    "bio_free",
    "uni_reg",
    "naive",
    "checkpoint_random",
]

network_options_1 = [
    "plain",
    "adjusted",
    "bio_trained",
    "naive",
]

network_options_1d = [
    "adjusted",
    "bio_trained",
    "naive",
]

network_options_2 = [
    "plain",
    "adjusted",
    "bio_trained",
    "naive",
    "bio_free",
    "uni_reg",
]


network_files = [
    "bkg_node_types.csv",
    "bkg_nodes.h5",
    "lgn_node_types.csv",
    "lgn_nodes.h5",
    "v1_node_types.csv",
    "v1_nodes.h5",
    "bkg_v1_edge_types.csv",
    "bkg_v1_edges.h5",
    "lgn_v1_edge_types.csv",
    "lgn_v1_edges.h5",
    "v1_v1_edge_types.csv",
    "v1_v1_edges.h5",
]
network_files = [f"/network/{file}" for file in network_files]

# drop bkg_v1_edge_types.csv because it will be overridden.
network_files = network_files[:6] + network_files[7:]

filter_files = [network_files[2], network_files[3]]  # just lgn nodes


networks = {
    "profile": {
        "radius": 100.0,
        "core_radius": 50.0,
        "other_options": "--small-lgn"
    },
    "tiny": {
        "radius": 50.0,
        "core_radius": 20.0,
        "other_options": "--small-lgn"
    },
    "small": {
        "radius": 200.0,
        "core_radius": 100.0,
        "other_options": "--small-lgn",
        "memory": 10
    },
    "core": {
        "radius": 400.0,
        "core_radius": 200.0,
        "memory": 20
    },
    "core_nll": {
        "radius": 400.0,
        "core_radius": 200.0,
        "memory": 20,
        "other_options": "-nll"
    },
    "full": {
        "radius": 700.0,
        "core_radius": 400.0,
        "memory": 80
    },
    "full_nll": {
        "radius": 700.0,
        "core_radius": 400.0,
        "memory": 80,
        "other_options": "-nll"
    }
}

# 10 randomised core networks (default)
for i in range(10):
    networks[f"core_{i}"] = {
        "radius": 400.0,
        "core_radius": 200.0,
        "memory": 20,
        "seed": i * 1000,
        "other_options": "--fluctuate-nneu"
    }
    networks[f"core_nll_{i}"] = {
        "radius": 400.0,
        "core_radius": 200.0,
        "memory": 20,
        "seed": i * 1000,
        "other_options": "--fluctuate-nneu -nll"
    }

# Add variant networks: core_{i}_{variant} and core_nll_{i}_{variant}
# These are always registered so multi-variant aggregate rules can reference them.
for variant in model_variants:
    for i in range(10):
        networks[f"core_{i}_{variant}"] = {
            "radius": 400.0,
            "core_radius": 200.0,
            "memory": 20,
            "seed": i * 1000,
            "other_options": "--fluctuate-nneu",
            "model_variant": variant,
        }
        networks[f"core_nll_{i}_{variant}"] = {
            "radius": 400.0,
            "core_radius": 200.0,
            "memory": 20,
            "seed": i * 1000,
            "other_options": "--fluctuate-nneu -nll",
            "model_variant": variant,
        }

# Apply variant suffix to the current session's default network set
# so that running with --config model_variant=X suffixes all standard targets
# as <network>_<variant>.
if vs:
    _base_networks = {k: v for k, v in networks.items()
                      if not v.get("model_variant")}
    _suffixed = {f"{k}{vs}": {**v, "model_variant": model_variant}
                 for k, v in _base_networks.items()}
    networks.update(_suffixed)


def _get_model_variant(network_name):
    return networks.get(network_name, {}).get("model_variant", "")


def _get_base_props(network_name):
    v = _get_model_variant(network_name)
    return f"base_props_{v}" if v else "base_props_default"


def _get_build_files(network_name):
    """Return the build-phase input files for a given network name."""
    bp = _get_base_props(network_name)
    return [
        f"{bp}/lgn_weights_population.csv",
        f"{bp}/lgn_params.csv",
        f"{bp}/lgn_models.csv",
        "glif_props/v1_node_models.csv",
        "glif_props/v1_edge_models.csv",
        "glif_props/lgn_weights_model.csv",
        "glif_props/bkg_weights_model.csv",
        "glif_models/cell_models/313861608_glif_lif_asc_config.json",
    ]


def _get_synaptic_model(network_name):
    """Return the synaptic model source path for a given network."""
    return "glif_models/synaptic_models/e4_to_e4.json"


# Precompute wildcard constraint patterns (avoids generator expressions in the
# wildcard_constraints block, which some Snakemake versions reject).
_network_name_constraint = "|".join(re.escape(k) for k in networks.keys())
_network_option_constraint = "|".join(network_options)
# setup marker slug is a variant name or the literal "default"
_setup_slug_constraint = "|".join(re.escape(v) for v in (model_variants + ["default"]))

# only include available ones
wildcard_constraints:
    network_name = _network_name_constraint,
    network_option = _network_option_constraint,
    slug = _setup_slug_constraint


n_threads = 8


# ============================================================
# Variant setup rule: (re)points the `base_props` symlink at the active
# source dir so scripts that hard-code "base_props/" read the correct files.
# The symlink is also established at parse time (see top of file); this rule
# keeps the dependency explicit in the DAG for build targets.
# `slug` is a variant name or the literal "default".
# NOTE: `rm -rf base_props` is safe because base_props is a managed symlink;
# the default data lives in base_props_default/ (see migration notes).
# ============================================================
rule setup_base_props:
    output: ".base_props_{slug}_setup"
    params:
        src=lambda w: "base_props_default" if w.slug == "default" else f"base_props_{w.slug}"
    shell:
        """
        rm -rf base_props
        ln -s {params.src} base_props
        touch {output}
        """


# ============================================================
# Pre-computed expand lists
# Snakemake 9.x rejects expand() with keyword arguments inside rule bodies;
# pre-compute them here as plain Python variables instead.
# ============================================================
_rcorr_inputs = expand(
    "core_nll_{i}" + vs + "/figures/response_correlation_{input_type}.png",
    i=range(10), input_type=network_options_1)
_contrast_inputs = expand(
    "core_nll_{i}" + vs + "/figures/contrast_responsive_cells_{input_type}.pdf",
    i=range(10), input_type=network_options_1)
_contrast_notf_inputs = expand(
    "core_nll_{i}" + vs + "/figures/contrast_responsive_cells_{input_type}.pdf",
    i=range(10), input_type=["plain", "adjusted"])
_rasters_inputs = expand(
    "core_nll_{i}" + vs + "/output_{input_type}/raster_and_spectra_by_tuning_angle.png",
    i=range(10), input_type=network_options_2)
_rasters_notf_inputs = expand(
    "core_nll_{i}" + vs + "/output_{input_type}/raster_and_spectra_by_tuning_angle.png",
    i=range(10), input_type=["plain", "adjusted"])
_odsi_inputs = expand(
    "core_nll_{i}" + vs + "/figures/OSI_DSI_{input_type}.png",
    i=range(10), input_type=network_options_1)
_odsi_notf_inputs = expand(
    "core_nll_{i}" + vs + "/figures/OSI_DSI_{input_type}.png",
    i=range(10), input_type=["plain", "adjusted"])
_core_nlls_plot_inputs = expand(
    "core_nll_{i}" + vs + "/output_adjusted/raster_and_spectra_by_tuning_angle.png",
    i=range(10))
_cores_inputs = expand("core_{i}" + vs + "/output_adjusted/spikes.h5", i=range(10))
_cores_plot_inputs = expand(
    "core_{i}" + vs + "/output_adjusted/raster_and_spectra_by_tuning_angle.png",
    i=range(10))
_agg_rcorr_inputs = expand(
    "aggregated_response_correlation" + vs + "/{input_type}.png",
    input_type=network_options_1)
_lifetime_sparsity_inputs = expand(
    "core_nll_{i}" + vs + "/metrics/lifetime_sparsity_{input_type}.npy",
    i=range(10), input_type=network_options_1)
_pop_sparsity_inputs = expand(
    "core_nll_{i}" + vs + "/metrics/population_sparsity_{input_type}.npy",
    i=range(10), input_type=network_options_1)
_lifetime_sparsity_outputs = expand(
    "lifetime_sparsity_core_nll_{i}_{input_type}" + vs + ".png",
    i=range(10), input_type=network_options_1)
_spectra_inputs = expand(
    "core_nll_{i}" + vs + "/contrasts_{input_type}/combined_spectra_700to2700.json",
    i=range(10), input_type=network_options_1)
_spectra_figs = expand(
    "core_nll_{i}" + vs + "/contrasts_{input_type}/figures",
    i=range(10), input_type=network_options_1)
_core0_contrast_inputs = expand(
    "core_nll_0" + vs + "/figures/contrast_responsive_cells_{input_type}.pdf",
    input_type=network_options_1)
_core0_rasters_inputs = expand(
    "core_nll_0" + vs + "/output_{input_type}/raster_and_spectra_by_tuning_angle.png",
    input_type=network_options_2)
_core0_odsi_inputs = expand(
    "core_nll_0" + vs + "/figures/OSI_DSI_{input_type}.png",
    input_type=network_options_1)
_core0_spectra_inputs = expand(
    "core_nll_0" + vs + "/contrasts_{input_type}/combined_spectra_700to2700.json",
    input_type=network_options_1)
_core0_spectra_figs = expand(
    "core_nll_0" + vs + "/contrasts_{input_type}/figures",
    input_type=network_options_1)
_var_rasters_inputs = expand(
    "core_nll_{i}_{variant}/output_{input_type}/raster_and_spectra_by_tuning_angle.png",
    variant=model_variants, i=range(10), input_type=network_options_2)
_var_contrast_inputs = expand(
    "core_nll_{i}_{variant}/figures/contrast_responsive_cells_{input_type}.pdf",
    variant=model_variants, i=range(10), input_type=network_options_1)
_var_odsi_inputs = expand(
    "core_nll_{i}_{variant}/figures/OSI_DSI_{input_type}.png",
    variant=model_variants, i=range(10), input_type=network_options_1)
_var_spikes_inputs = expand(
    "core_nll_{i}_{variant}/output_{input_type}/spikes.h5",
    variant=model_variants, i=range(10), input_type=["plain", "adjusted"])
_var_spectra_inputs = expand(
    "core_nll_{i}_{variant}/contrasts_{input_type}/combined_spectra_700to2700.json",
    variant=model_variants, i=range(10), input_type=network_options_1)


# ============================================================
# Aggregate rules (default variant, prefixed when --config is used)
# ============================================================
rule all_cores_nll_response_corr_plot:
    input: _rcorr_inputs

rule all_cores_nll_contrast_plot:
    input: _contrast_inputs

rule all_cores_nll_contrast_plot_notf:
    input: _contrast_notf_inputs

rule all_cores_nll_rasters:
    input: _rasters_inputs

rule all_cores_nll_rasters_notf:
    input: _rasters_notf_inputs

rule all_core_nll_odsi_plots:
    input: _odsi_inputs

rule all_core_nll_odsi_plots_notf:
    input: _odsi_notf_inputs

rule all_cores_notf:
    input:
        rules.all_cores_nll_contrast_plot_notf.input,
        rules.all_cores_nll_rasters_notf.input,
        rules.all_core_nll_odsi_plots_notf.input

rule all_cores_all:
    input:
        rules.all_cores_nll_contrast_plot.input,
        rules.all_cores_nll_rasters.input,
        rules.all_core_nll_odsi_plots.input

rule all_core_nlls_plot:
    input: _core_nlls_plot_inputs

rule all_cores:
    input: _cores_inputs

rule all_cores_plot:
    input: _cores_plot_inputs

rule all:
    input: f"small{vs}/figures/OSI_DSI.png"

rule core_spikes:
    input: f"core{vs}/output_adjusted/spikes.h5"

rule clean:
    shell:
        """
        rm -rf cell_types
        rm -rf glif_models
        rm -rf glif_props
        rm -rf glif_requisite
        rm -rf full
        rm -rf small
        rm -rf core
        rm -rf tiny
        rm -rf profile
        rm -rf out.prof
        rm -f base_props .base_props_*_setup
        """


# ============================================================
# Preprocessing / intermediate rules
# ============================================================

rule tf_alpha_params:
    input:
        script="extract_tau_syns.py",
        data=[
            f"{base_props_dir}/tau_syn_fast.csv",
            f"{base_props_dir}/tau_syn_slow.csv",
            f"{base_props_dir}/amp_slow.csv",
        ] + setup_deps
    output:
        f"{tf_props_dir}/double_alpha_params.csv",
        f"{tf_props_dir}/double_alpha_params_full.csv",
    params:
        tf_props_dir=tf_props_dir
    shell: "TF_PROPS_DIR={params.tf_props_dir} python {input.script}"

rule tf_basis_functions:
    input:
        script="bf_conv.py",
        data=[
            f"{tf_props_dir}/double_alpha_params.csv",
            f"{tf_props_dir}/double_alpha_params_full.csv"
        ]
    output:
        f"{tf_props_dir}/tau_basis.npy",
        f"{tf_props_dir}/basis_function_weights.csv"
    params:
        tf_props_dir=tf_props_dir
    shell: "TF_PROPS_DIR={params.tf_props_dir} python {input.script}"


rule synaptic_models:
    input:
        script="create_syn_models.py",
        data=[
            f"{base_props_dir}/tau_syn_fast.csv",
            f"{base_props_dir}/tau_syn_slow.csv",
            f"{base_props_dir}/amp_slow.csv",
        ] + setup_deps
    output: "glif_models/synaptic_models/e4_to_e4.json"  # representative model
    shell: "python {input.script}"

rule glif_explained_variance_ratio:
    input: "query_glif_expvar.py"
    output: "cell_types/glif_explained_variance_ratio.csv"
    shell: "python {input}"


rule cells_with_glif_pop_name:
    input:
        script="pick_glif_all.py",
        data=[
            f"{base_props_dir}/V1model_seed_file.xlsx",
            "cell_types/glif_explained_variance_ratio.csv"
        ] + setup_deps
    output: "cell_types/cells_with_glif_pop_name.csv"
    shell: "python {input.script}"


rule cell_models:
    input:
        script="prepare_glif_models.py",
        data="cell_types/cells_with_glif_pop_name.csv"
    output: "glif_models/cell_models/313861608_glif_lif_asc_config.json"  # representative
    shell: "python {input.script}"


rule glif_models_prop:
    input:
        script="make_glif_models_prop.py",
        data="cell_types/cells_with_glif_pop_name.csv"
    output:
        "glif_requisite/glif_models_prop.csv"
    shell: "python {input.script}"


rule glif_requirements:
    input:
        script="make_glif_requirements.py",
        data=[
            f"{base_props_dir}/V1model_seed_file.xlsx",
            "glif_requisite/glif_models_prop.csv"
        ] + setup_deps
    output: "glif_props/v1_node_models.csv"
    shell: "python {input.script} --double-alpha"


rule v1_edge_model:
    input:
        script="make_v1_edge_models.py",
        data=[
            f"{base_props_dir}/cell_type_naming_scheme.csv",
            "glif_requisite/glif_models_prop.csv",
            "precomputed_props/v1_synapse_amps.json",
            f"{base_props_dir}/sigma.csv",
            f"{base_props_dir}/pmax_matrix_v1dd.csv",
            f"{base_props_dir}/b_ratio.csv",
            f"{base_props_dir}/psp_lookup_table.csv",
            f"{base_props_dir}/psp_characterization.csv",
            f"{base_props_dir}/syn_types_latency.csv"
        ] + setup_deps
    output: "glif_props/v1_edge_models.csv"
    shell: "python {input.script}"


rule lgn_weight_model:
    input:
        script="make_lgn_weights.py",
        data=[
            f"{base_props_dir}/lgn_weights_population.csv",
            "glif_props/v1_node_models.csv",
            "precomputed_props/v1_synapse_amps.json"
        ] + setup_deps
    output: "glif_props/lgn_weights_model.csv"
    shell: "python {input.script} --double-alpha"


rule bkg_weight_model:
    input:
        script="make_bkg_weights.py",
        data=[
            f"{base_props_dir}/bkg_weights_population_init.csv",
            "glif_props/v1_node_models.csv",
            "precomputed_props/v1_synapse_amps.json"
        ] + setup_deps
    output: "glif_props/bkg_weights_model.csv"
    shell: "python {input.script}"


# ============================================================
# Network building rules
# ============================================================

rule build_network:
    input:
        script=main_scripts,
        data=lambda wildcards: _get_build_files(wildcards.network_name) + setup_deps
    output: ["{network_name}" + name for name in network_files]
    threads: n_threads
    params:
        radius=lambda wildcards: networks[wildcards.network_name]["radius"],
        core_radius=lambda wildcards: networks[wildcards.network_name]["core_radius"],
        seed=lambda wildcards: networks[wildcards.network_name].get("seed", 153),
        other_options=lambda wildcards: networks[wildcards.network_name].get("other_options", "")
    shell:
        "mpirun -np {n_threads} python {input.script[0]} -f "
        "-o {wildcards.network_name}/network "
        "--radius {params.radius} --core-radius {params.core_radius} "
        "--seed {params.seed} {params.other_options}"


rule bkg_edges_override:
    input:
        "precomputed_props/bkg_v1_edge_types.csv",
        "{network_name}/network/bkg_nodes.h5",
        "{network_name}/components/synaptic_models/e4_to_e4.json"
    output: "{network_name}/network/bkg_v1_edge_types.csv"
    shell: "cp {input[0]} {output}"


rule bkg_spikes:
    input:
        script=["bkg_spike_generation.py", "stimulus_trials.py"],
        network=[
            "{network_name}/network/bkg_nodes.h5",
            "{network_name}/network/bkg_v1_edge_types.csv",
        ]
    output:
        "{network_name}/bkg/bkg_spikes_250Hz_3s.h5",
        "{network_name}/bkg/bkg_spikes_250Hz_10s.h5"
    shell: "python {input.script[0]} {wildcards.network_name}"


rule network_synaptic_components:
    input:
        script="convert_models.py",
        data=lambda wildcards: [
            f"{wildcards.network_name}/network/bkg_nodes.h5",
            _get_synaptic_model(wildcards.network_name),
        ]
    output: "{network_name}/components/synaptic_models/e4_to_e4.json"
    shell: "python {input.script} {wildcards.network_name}"


rule config_files:
    input: [f"config_templates/{fname}" for fname in config_files]
    output: ["{network_name}" + f"/configs/{fname}" for fname in config_files] + ["{network_name}/configs/config.json"]
    shell: """
        mkdir -p {wildcards.network_name}/configs
        cp config_templates/*.json {wildcards.network_name}/configs
        ln -s config_adjusted.json {wildcards.network_name}/configs/config.json
    """


rule filternet_spikes:
    input:
        script="run_filternet.py",
        network=["{network_name}" + name for name in filter_files],
        config="{network_name}/configs/config_filternet.json"
    output: "{network_name}/filternet/spikes.h5"
    threads: n_threads
    shell: "mpirun -np {n_threads} python {input.script} {input.config}"


rule filternet_bkgtune_spikes:
    input:
        script="run_filternet.py",
        network=["{network_name}" + name for name in filter_files],
        config="{network_name}/configs/config_filternet_bkgtune.json"
    output: "{network_name}/filternet_bkgtune/spikes.h5"
    threads: n_threads
    shell: "mpirun -np {n_threads} python {input.script} {input.config}"


rule output_spikes:
    input:
        script="run_pointnet.py",
        network=["{network_name}" + name for name in network_files],
        adjusted=lambda wildcards: f"{wildcards.network_name}/network/v1_v1_edges_adjusted.h5" if wildcards.run_opt == "_adjusted" else [],
        config="{network_name}/configs/config{run_opt}.json",
        components="{network_name}/components/synaptic_models/e4_to_e4.json",
        data=[
            "{network_name}/filternet/spikes.h5",
            "{network_name}/bkg/bkg_spikes_250Hz_3s.h5",
        ]
    output: "{network_name}/output{run_opt}/spikes.h5"
    threads: n_threads
    shell: "python {input.script} {input.config} -n {n_threads}"


rule output_rasters:
    input:
        script="plot_raster.py",
        data="{network_name}/output{run_opt}/spikes.h5",
    output: "{network_name}/output{run_opt}/raster_and_spectra_by_tuning_angle.png"
    shell: "python {input.script} {wildcards.network_name}/output{wildcards.run_opt}"


rule output_spikes_bkgtune:
    input:
        script="run_pointnet.py",
        network=["{network_name}" + name for name in network_files],
        config="{network_name}/configs/config_bkgtune.json",
        components="{network_name}/components/synaptic_models/e4_to_e4.json",
        data=[
            "{network_name}/filternet_bkgtune/spikes.h5",
            "{network_name}/bkg/bkg_spikes_250Hz_10s.h5",
        ]
    output: "{network_name}/output_bkgtune/spikes.h5"
    threads: n_threads
    shell: "python {input.script} {input.config} -n {n_threads}"


rule actuation_matrix:
    input:
        script="plot_actuation_matrix.py",
        network=["{network_name}" + name for name in network_files],
        data="neuropixels/metrics/OSI_DSI_DF_data.csv"
    output:
        "{network_name}/metrics/actuation_matrix.csv",
        "{network_name}/figures/actuation_matrix.pdf"
    params:
        core_radius=lambda wildcards: networks[wildcards.network_name]["core_radius"]
    shell: "python {input.script} {wildcards.network_name} -c {params.core_radius}"


rule model_target_current:
    input:
        script="calculate_target_current.py",
        data=[
            "neuropixels/metrics/OSI_DSI_DF_data.csv",
            "glif_requisite/glif_models_prop.csv",
            "glif_models/if_curves_all.csv"
        ]
    output: "glif_models/target_currents.csv"
    shell: "python {input.script}"


rule if_curves:
    input:
        script="calculate_if_curves.py",
        data=[
            "glif_requisite/glif_models_prop.csv",
            "glif_models/cell_models/313861608_glif_lif_asc_config.json"
        ]
    output:
        "glif_models/if_curves_all.csv",
    shell: "python {input.script}"


rule current_adjustment_factor:
    input:
        script="calculate_adjustment_factor.py",
        network="{network_name}/metrics/actuation_matrix.csv",
        data="glif_models/target_currents.csv"
    output: "{network_name}/metrics/modulation.csv"
    shell: "python {input.script} {wildcards.network_name}"


rule recurrent_edge_adjustment:
    input:
        script="make_adjusted_network.py",
        network=["{network_name}" + name for name in network_files],
        data="{network_name}/metrics/modulation.csv"
    output: "{network_name}/network/v1_v1_edges_adjusted.h5"
    shell: "python {input.script} {wildcards.network_name}"


rule filternet_osi_job:
    input:
        script="make_osi_jobs.py",
        network=["{network_name}" + name for name in filter_files],
        data="{network_name}/configs/config_filternet.json"
    output: "{network_name}/jobs/filternet_8dir_10trials.sh"
    shell: "python {input.script} {wildcards.network_name} --filternet"


rule osi_job:
    input:
        script="make_osi_jobs.py",
        network=["{network_name}" + name for name in network_files],
        adjusted="{network_name}/network/v1_v1_edges_adjusted.h5",
        data="{network_name}/configs/config.json"
    output: "{network_name}/jobs/8dir_10trials_{network_option}.sh"
    params: memory=lambda wildcards: networks[wildcards.network_name]["memory"]
    shell: "python {input.script} {wildcards.network_name} --memory {params.memory} --network_option {wildcards.network_option}"


rule filternet_contrast_job:
    input:
        script="make_contrast_jobs.py",
        network=["{network_name}" + name for name in filter_files],
        data="{network_name}/configs/config_filternet.json"
    output: "{network_name}/jobs/filternet_contrasts.sh"
    shell: "python {input.script} {wildcards.network_name} --filternet"


rule contrast_job:
    input:
        script=["make_contrast_jobs.py", "stimulus_trials.py"],
        network=["{network_name}" + name for name in network_files],
        adjusted="{network_name}/network/v1_v1_edges_adjusted.h5",
        data="{network_name}/configs/config.json"
    output: "{network_name}/jobs/contrasts_{network_option}.sh"
    params: memory=lambda wildcards: networks[wildcards.network_name]["memory"]
    shell: "python {input.script[0]} {wildcards.network_name} --memory {params.memory} --network_option {wildcards.network_option}"


curdir = os.getcwd()

rule run_filternet_osi_job:
    input:
        script="{network_name}/jobs/filternet_8dir_10trials.sh"
    output: "{network_name}/filternet_8dir_10trials/angle0_trial0/spikes.h5"
    params: curdir=curdir
    shell: "ssh hpc-login 'cd {params.curdir}; sbatch --wait {input.script}'"


rule run_osi_job:
    input:
        script="{network_name}/jobs/8dir_10trials_{network_option}.sh",
        data=["{network_name}/filternet_8dir_10trials/angle0_trial0/spikes.h5",
              "{network_name}/bkg/bkg_spikes_250Hz_3s.h5"],
        components="{network_name}/components/synaptic_models/e4_to_e4.json"
    output: "{network_name}/8dir_10trials_{network_option}/angle0_trial0/spikes.h5"
    params: curdir=curdir
    shell: "ssh hpc-login 'cd {params.curdir}; sbatch --wait {input.script}'"


rule run_filternet_contrast_job:
    input:
        script="{network_name}/jobs/filternet_contrasts.sh"
    output: "{network_name}/filternet_contrasts/angle0_contrast0.05_trial0/spikes.h5"
    params: curdir=curdir
    shell: "ssh hpc-login 'cd {params.curdir}; sbatch --wait {input.script}'"

rule run_contrast_job:
    input:
        script="{network_name}/jobs/contrasts_{network_option}.sh",
        network="{network_name}/network/v1_v1_edges_checkpoint.h5",
        data=["{network_name}/filternet_contrasts/angle0_contrast0.05_trial0/spikes.h5",
              "{network_name}/bkg/bkg_spikes_250Hz_3s.h5"],
        components="{network_name}/components/synaptic_models/e4_to_e4.json"
    output: "{network_name}/contrasts_{network_option}/angle0_contrast0.05_trial0/spikes.h5"
    params: curdir=curdir
    shell: "ssh hpc-login 'cd {params.curdir}; sbatch --wait {input.script}'"


rule contrast_spike_aggregation:
    input:
        script="contrast_spike_aggregation.py",
        data="{network_name}/contrasts_{network_option}/angle0_contrast0.05_trial0/spikes.h5"
    output: "{network_name}/contrasts_{network_option}/spike_counts.npz"
    shell: "python {input.script} {wildcards.network_name} {wildcards.network_option}"

rule plot_contrast_response:
    input:
        script="contrast_analysis.py",
        data="{network_name}/contrasts_{network_option}/spike_counts.npz"
    output: "{network_name}/figures/contrast_responsive_cells_{network_option}.pdf"
    shell: "python {input.script} {wildcards.network_name} {wildcards.network_option}"

rule odsi_metrics:
    input:
        script="calculate_odsi.py",
        data="{network_name}/8dir_10trials_{network_option}/angle0_trial0/spikes.h5"
    output: "{network_name}/metrics/OSI_DSI_DF_{network_option}.csv"
    shell: "python {input.script} {wildcards.network_name} {wildcards.network_option}"


rule plot_odsi:
    input:
        script="plot_odsi.py",
        data="{network_name}/metrics/OSI_DSI_DF_{network_option}.csv"
    output: "{network_name}/figures/OSI_DSI_{network_option}.png"
    shell: "python {input.script} {wildcards.network_name} {wildcards.network_option}"


rule bkg_adjustment:
    input:
        config=f"small{vs}/output_bkgtune/spikes.h5"
    output: f"small{vs}/network/bkg_v1_edge_types_adjusted.csv"
    threads: n_threads
    shell: f"""
        python bkg_weight_adjustment.py
        cp small{vs}/network/bkg_v1_edge_types.csv small{vs}/network/bkg_v1_edge_types_adjusted.csv
        """


rule graph:
    shell: "snakemake --dag | dot -Tpdf > workflow_graph.pdf"


rule profile_build:
    input: [f"profile{vs}" + name for name in network_files]
    output: "out.prof"
    shell: f"python -m cProfile -o out.prof build_network.py -f -o profile{vs}/network --radius 100.0 --core-radius 50.0"


rule clear_logs:
    shell: "rm */jobs/logs/*"

rule response_correlation_calculation:
    input:
        network_files=[
            "{network_name}/network/v1_nodes.h5",
            "{network_name}/network/v1_v1_edges.h5"
        ],
        activity_files=[
            "{network_name}/metrics/stim_spikes_output_imagenet_checkpoint.npz",
            "{network_name}/metrics/stim_spikes_output_imagenet.npz"
        ]
    output:
        correlations="{network_name}/metrics/response_correlations_{input_type}.npy",
    threads: 8,
    params:
        base_dir="{network_name}",
        input_type="{input_type}"
    shell:
        """
        python response_correlation_calculations.py --base_dir {params.base_dir} --input_type {params.input_type}
        """

rule calculate_distances:
    input:
        network_files=[
            "{network_name}/network/v1_nodes.h5",
            "{network_name}/network/v1_v1_edges.h5"
        ]
    output:
        distances="{network_name}/metrics/distances.npy"
    params:
        base_dir="{network_name}"
    shell:
        """
        python calculate_distances.py --base_dir {params.base_dir}
        """

rule response_correlation_plot:
    input:
        script="response_correlation_plot.py",
        correlations="{network_name}/metrics/response_correlations_{input_type}.npy",
        distances="{network_name}/metrics/distances.npy"
    output:
        plot="{network_name}/figures/response_correlation_{input_type}.png"
    params:
        base_dir="{network_name}",
        input_type="{input_type}"
    shell:
        """
        python response_correlation_plot.py {params.base_dir} {params.input_type}
        """

rule aggregate_correlation_plot:
    input:
        script="aggregate_correlation_plot.py",
        data="core_nll_9" + vs + "/metrics/response_correlations_{input_type}.npy",
    output:
        "aggregated_response_correlation" + vs + "/{input_type}.png"
    params:
        vs=vs
    shell:
        """
        mkdir -p aggregated_response_correlation{params.vs}
        python {input.script} core_nll_?{params.vs} {wildcards.input_type} aggregated_response_correlation{params.vs}/{wildcards.input_type}.png
        """

rule all_response_correlation_plots:
    input: _rcorr_inputs + _agg_rcorr_inputs


# Rule to calculate sparsity measures
rule calculate_sparsity:
    input:
        script="sparsity_calculations.py",
        activity_files=[
            "{base_dir}/metrics/stim_spikes_output_imagenet.npz",
            "{base_dir}/metrics/stim_spikes_output_imagenet_checkpoint.npz"
        ]
    output:
        lifetime_sparsity="{base_dir}/metrics/lifetime_sparsity_{input_type}.npy",
        population_sparsity="{base_dir}/metrics/population_sparsity_{input_type}.npy"
    params:
        base_dir="{base_dir}",
        input_type="{input_type}"
    threads: 8
    shell:
        """
        python {input.script} --base_dir {params.base_dir} --input_type {params.input_type}
        """

rule all_nll_sparsity:
    input: _lifetime_sparsity_inputs + _pop_sparsity_inputs

rule plot_population_sparsity:
    input: _pop_sparsity_inputs
    output:
        "population_sparsity_{input_type}.png"
    params:
        script="plot_sparsity.py",
        base_dirs=[f"core_nll_{i}{vs}" for i in range(10)],
        input_type="{input_type}",
        output_dir="."
    shell:
        """
        python {params.script} --base_dirs {params.base_dirs} --input_type {params.input_type} --output_dir {params.output_dir}
        """

rule plot_lifetime_sparsity:
    input: _lifetime_sparsity_inputs
    output: _lifetime_sparsity_outputs
    params:
        script="plot_sparsity.py",
        base_dirs=[f"core_nll_{i}{vs}" for i in range(10)],
        input_type="{input_type}",
        output_dir="."
    shell:
        """
        python {params.script} --base_dirs {params.base_dirs} --input_type {params.input_type} --output_dir {params.output_dir}
        """


# Rule to run spectral analysis for a single network and input type
rule spectral_analysis:
    input:
        script="spectral_analysis2.py",
        data="{network_name}/contrasts_{network_option}/angle0_contrast0.05_trial0/spikes.h5"
    output:
        "{network_name}/contrasts_{network_option}/combined_spectra_700to2700.json"
    threads: 8
    shell:
        """
        python {input.script} \
        --basedir {wildcards.network_name} \
        --subdir contrasts_{wildcards.network_option} \
        --n_processes {threads} \
        """

rule spectral_plots:
    input:
        script="spectral_analysis2.py",
        data="{network_name}/contrasts_{network_option}/combined_spectra_700to2700.json"
    output:
        directory("{network_name}/contrasts_{network_option}/figures")
    shell:
        """
        python {input.script} \
        --basedir {wildcards.network_name} \
        --subdir contrasts_{wildcards.network_option} \
        --plot_only
        """

rule all_spectral_analysis:
    input: _spectra_inputs

rule all_spectral_plots:
    input: _spectra_figs

rule aggregate_spectra:
    input:
        script="aggregate_spectra.py",
        data=_spectra_inputs
    output:
        directory("aggregate_spectra" + vs)
    params:
        base_dirs=" ".join([f"core_nll_{i}{vs}" for i in range(10)])
    shell:
        """
        python {input.script} \
        --base_dirs {params.base_dirs} \
        --input_types plain bio_trained naive adjusted \
        --output_dir {output}
        """

rule aggregate_spectra_normalized:
    input:
        script="aggregate_spectra.py",
        data=_spectra_inputs
    output:
        directory("aggregate_spectra_normalized" + vs)
    params:
        base_dirs=" ".join([f"core_nll_{i}{vs}" for i in range(10)])
    shell:
        """
        python {input.script} \
        --base_dirs {params.base_dirs} \
        --input_types plain bio_trained naive adjusted \
        --output_dir {output} \
        --normalized
        """

rule all_spectral:
    input:
        rules.all_spectral_analysis.input,
        rules.all_spectral_plots.input,
        rules.aggregate_spectra.output,

rule all_core_nll_0_all:
    input:
        _core0_contrast_inputs +
        _core0_rasters_inputs +
        _core0_odsi_inputs +
        _core0_spectra_inputs +
        _core0_spectra_figs


# ============================================================
# Multi-variant aggregate rules
# Use these to check or gather outputs across ALL model variants.
# NOTE: Each variant's outputs must be built separately via
#   snakemake --config model_variant=VARIANT <target>
# before these rules can find them.
# ============================================================

rule all_variants_cores_nll_rasters:
    """Raster plots for all 10 seeds across every model variant."""
    input: _var_rasters_inputs

rule all_variants_cores_nll_contrast_plots:
    """Contrast response plots for all seeds across every model variant."""
    input: _var_contrast_inputs

rule all_variants_core_nll_odsi_plots:
    """OSI/DSI plots for all seeds across every model variant."""
    input: _var_odsi_inputs

rule all_variants_cores_nll_spikes:
    """Spike outputs for all seeds across every model variant (plain + adjusted)."""
    input: _var_spikes_inputs

rule all_variants_spectral_analysis:
    """Spectral analysis for all seeds across every model variant."""
    input: _var_spectra_inputs

rule all_variants_all:
    """Run all primary analyses for every model variant."""
    input:
        rules.all_variants_cores_nll_contrast_plots.input,
        rules.all_variants_cores_nll_rasters.input,
        rules.all_variants_core_nll_odsi_plots.input,
