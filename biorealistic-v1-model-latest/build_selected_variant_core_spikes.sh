#!/bin/bash
# Build core_<variant>/output_plain/spikes.h5 for a selected set of model variants.
#
# Each variant runs in its OWN `snakemake ... --config model_variant=<v>` invocation,
# sequentially. They CANNOT be combined into one run or parallelized: the base_props
# symlink and the shared preprocessing dirs (glif_props/, cell_types/, glif_models/,
# glif_requisite/) hold one variant at a time, so concurrent/combined builds collide.
# (For the same reason this is a plain script, not a snakemake rule -- a rule that
# shelled out to snakemake would deadlock on the working-directory lock.)
#
# Cores come from profiles/default/config.yaml (cores: 8). Add/override snakemake
# flags by passing them through; they are inserted BEFORE the target so --config
# stays last (see the --config arg-order note in README.md). Examples:
#   conda activate osc-mouse-v1-model
#   ./build_selected_variant_core_spikes.sh
#   ./build_selected_variant_core_spikes.sh --cores 16
#   ./build_selected_variant_core_spikes.sh --rerun-incomplete
#
# Re-running is safe: snakemake skips variants already built.

set -uo pipefail
cd "$(dirname "$0")" || exit 1

VARIANTS=(
    "i4Pvalb-like-i4Sst",
    "i4Sst-like-i4Pvalb",
    "L4-cell-vol-dens-conn-as-L6",
    "L4-cell-volume-density-as-L6",
    "L4-connectivity-as-L6",
    "L4-syn-as-L6-syn",
    "L4-e2e-syn-as-L6",
    "L4-e2i-syn-as-L6",
    "L4-i2e-syn-as-L6",
    "L4-Pvalb2e-as-L6",
    "L4-Pvalb2e-syn-lat-as-L6",
    "L4-Pvalb2e-syn-tau-amp-as-L6",
    "L4-Sst2e-as-L6",
    "L4-Sst2e-syn-lat-as-L6",
    "L4-Sst2e-syn-tau-amp-as-L6",
    "L4-Vip2e-syn-lat-as-L6",
    "L4-Vip2e-syn-tau-amp-as-L6",
    "L6-as-L4",
    "L6-syn-as-L4-syn",
)

if ! command -v snakemake >/dev/null 2>&1; then
    echo "ERROR: 'snakemake' not found on PATH. Activate the env first: conda activate osc-mouse-v1-model" >&2
    exit 1
fi

logdir="logs_variant_sweep"
mkdir -p "$logdir"

ok=(); failed=()
n=${#VARIANTS[@]}
i=0
for v in "${VARIANTS[@]}"; do
    i=$((i + 1))
    target="core_${v}/output_plain/spikes.h5"
    echo ""
    echo "==================================================================="
    echo "[$i/$n] $target   (model_variant=$v)"
    echo "==================================================================="
    if snakemake "$@" "$target" --config "model_variant=${v}" 2>&1 | tee "$logdir/${v}.log"; then
        ok+=("$v")
    else
        echo "!! FAILED: $v  (see $logdir/${v}.log)"
        failed+=("$v")
    fi
done

echo ""
echo "==================== SWEEP SUMMARY ===================="
echo "Succeeded: ${#ok[@]}/$n"
if [ "${#failed[@]}" -gt 0 ]; then
    echo "Failed:    ${#failed[@]}/$n"
    printf '  - %s\n' "${failed[@]}"
    exit 1
fi
echo "All ${n} variants built."
