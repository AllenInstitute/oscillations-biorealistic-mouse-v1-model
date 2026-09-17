#!/usr/bin/env bash
# Copy biorealistic-v1-model-latest/core_<suffix>/network into
# V1_GLIF_model_tf_training/GLIF_network_<suffix>.
#
# Usage:
#   ./copy_glif_network.sh                  # copy all core_* variants
#   ./copy_glif_network.sh -s <suffix>      # copy one specific variant
#   ./copy_glif_network.sh -c               # copy core/network → GLIF_network

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LATEST="$(dirname "$SCRIPT_DIR")/biorealistic-v1-model-latest"

usage() {
    echo "Usage: $0 [-s <network_suffix>] [-c]"
    echo "  -s  Variant suffix (e.g. L4-e2e-syn-as-L6). Omit to copy all core_* variants."
    echo "  -c  Copy core/network (baseline, no suffix) → GLIF_network."
    exit 1
}

SUFFIX=""
CORE_ONLY=0
while getopts ":s:ch" opt; do
    case $opt in
        s) SUFFIX="$OPTARG" ;;
        c) CORE_ONLY=1 ;;
        h) usage ;;
        :) echo "Option -$OPTARG requires an argument." >&2; usage ;;
        \?) echo "Unknown option: -$OPTARG" >&2; usage ;;
    esac
done

copy_subdirs() {
    # copy_subdirs <src_core_dir> <dest_name>
    # Creates dest_name/{network,components} from src_core_dir/{network,components}.
    local src_core="$1"
    local dest_name="$2"
    local dest="$SCRIPT_DIR/$dest_name"

    if [[ ! -d "$src_core/network" ]]; then
        echo "WARNING: source not found: $src_core/network" >&2
        return 1
    fi

    if [[ -d "$dest" ]]; then
        echo "SKIP (already exists): $dest_name"
        return 0
    fi

    mkdir -p "$dest"
    cp -r "$src_core/network" "$dest/network"
    cp -r "$src_core/components" "$dest/components"
    echo "DONE: $dest_name"
}

copy_one() {
    local suffix="$1"
    copy_subdirs "$LATEST/core_${suffix}" "GLIF_network_${suffix}"
}

copy_core() {
    copy_subdirs "$LATEST/core" "GLIF_network"
}

if [[ "$CORE_ONLY" -eq 1 ]]; then
    copy_core
elif [[ -n "$SUFFIX" ]]; then
    copy_one "$SUFFIX"
else
    found=0
    for core_dir in "$LATEST"/core_*/; do
        variant="${core_dir%/}"
        variant="${variant##*/core_}"
        if [[ -d "$core_dir/network" ]]; then
            copy_one "$variant"
            ((found++)) || true
        else
            echo "SKIP (no network subdir): core_${variant}" >&2
        fi
    done
    echo "Done. Processed $found variant(s)."
fi
