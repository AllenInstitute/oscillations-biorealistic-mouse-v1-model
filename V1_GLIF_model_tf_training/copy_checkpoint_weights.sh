#!/usr/bin/env bash
# Copy optimised *_<suffix>.h5 edge files produced by checkpoint_to_edges.py
# from V1_GLIF_model_tf_training/GLIF_network*/network/ into
# biorealistic-v1-model-latest/core*/network/.
#
# Usage:
#   ./copy_checkpoint_weights.sh                        # all GLIF_network_* variants
#   ./copy_checkpoint_weights.sh -c                     # core baseline (no variant suffix)
#   ./copy_checkpoint_weights.sh -v L6-as-L4            # one specific variant
#   ./copy_checkpoint_weights.sh --suffix bio_trained   # custom suffix (default: checkpoint)
#   ./copy_checkpoint_weights.sh -c --force             # overwrite existing files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LATEST="$(dirname "$SCRIPT_DIR")/biorealistic-v1-model-latest"

usage() {
    echo "Usage: $0 [-c] [-v <variant>] [--suffix <suffix>] [--force]"
    echo "  -c           Copy core baseline (GLIF_network → core/network)."
    echo "  -v <variant> Model variant suffix (e.g. L6-as-L4). Omit to copy all variants."
    echo "  --suffix <s> Edge-file suffix written by checkpoint_to_edges.py (default: checkpoint)."
    echo "  --force      Overwrite existing files."
    exit 1
}

VARIANT=""
CORE_ONLY=0
SUFFIX="checkpoint"
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c)         CORE_ONLY=1; shift ;;
        -v)         VARIANT="${2:?'-v requires an argument'}"; shift 2 ;;
        --suffix)   SUFFIX="${2:?'--suffix requires an argument'}"; shift 2 ;;
        --force)    FORCE=1; shift ;;
        -h|--help)  usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

FILES=("v1_v1_edges_${SUFFIX}.h5" "bkg_v1_edges_${SUFFIX}.h5")

copy_files() {
    local src_network="$1"   # full path to source network/ dir
    local dst_network="$2"   # full path to destination network/ dir
    local label="$3"

    if [[ ! -d "$src_network" ]]; then
        echo "WARNING: source not found: $src_network" >&2
        return 1
    fi
    if [[ ! -d "$dst_network" ]]; then
        echo "WARNING: destination not found: $dst_network" >&2
        return 1
    fi

    local copied=0
    for fname in "${FILES[@]}"; do
        local src="$src_network/$fname"
        local dst="$dst_network/$fname"

        if [[ ! -f "$src" ]]; then
            echo "WARNING: source file missing: $src" >&2
            continue
        fi

        if [[ -f "$dst" && "$FORCE" -eq 0 ]]; then
            echo "SKIP (exists, use --force to overwrite): $label/$fname"
            continue
        fi

        cp "$src" "$dst"
        echo "DONE: $label/$fname"
        ((copied++)) || true
    done
    [[ $copied -eq 0 ]] || echo "  → copied $copied file(s) to $dst_network"
}

if [[ "$CORE_ONLY" -eq 1 ]]; then
    copy_files \
        "$SCRIPT_DIR/GLIF_network/network" \
        "$LATEST/core/network" \
        "core"

elif [[ -n "$VARIANT" ]]; then
    copy_files \
        "$SCRIPT_DIR/GLIF_network_${VARIANT}/network" \
        "$LATEST/core_${VARIANT}/network" \
        "core_${VARIANT}"

else
    found=0
    for glif_dir in "$SCRIPT_DIR"/GLIF_network_*/; do
        [[ -d "$glif_dir" ]] || continue
        variant="${glif_dir%/}"
        variant="${variant##*/GLIF_network_}"
        copy_files \
            "$glif_dir/network" \
            "$LATEST/core_${variant}/network" \
            "core_${variant}"
        ((found++)) || true
    done
    echo "Done. Processed $found variant(s)."
fi
