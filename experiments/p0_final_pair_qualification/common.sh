#!/usr/bin/env bash
set -euo pipefail

p0_qualification_main() {
    local task="$1" legacy_launcher="$2" data_check="$3"
    shift 3
    local exp_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    local siderius_checkout="" workspace="" data_dir="" dry_run=0
    local -a fixed_args=()
    while [[ $# -gt 0 && "$1" != -- ]]; do fixed_args+=("$1"); shift; done
    [[ $# -gt 0 ]] || { echo "wrapper configuration missing separator" >&2; return 2; }
    shift
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --siderius-checkout|--workspace|--data_dir)
                [[ $# -ge 2 ]] || { echo "missing value for $1" >&2; return 2; }
                case "$1" in
                    --siderius-checkout) siderius_checkout="$2" ;;
                    --workspace) workspace="$2" ;;
                    --data_dir) data_dir="$2" ;;
                esac
                shift 2 ;;
            --dry-run|--dry_run) dry_run=1; shift ;;
            -h|--help) echo "Usage: bash experiments/$task/p0_final_pair_qualification/launch.sh --siderius-checkout DIR --workspace DIR --data_dir DIR [--dry-run]"; return 0 ;;
            *) echo "unknown argument: $1" >&2; return 2 ;;
        esac
    done
    [[ -n "$siderius_checkout" && -d "$siderius_checkout" ]] || { echo "--siderius-checkout must name a directory" >&2; return 2; }
    [[ -n "$workspace" ]] || { echo "missing required argument --workspace" >&2; return 2; }
    [[ ! -e "$workspace" || -d "$workspace" ]] || { echo "--workspace must be a directory or a new path" >&2; return 2; }
    if [[ -d "$workspace" && -n "$(find "$workspace" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then echo "--workspace must be empty: $workspace" >&2; return 2; fi
    [[ -d "$data_dir" ]] || { echo "--data_dir must name a directory" >&2; return 2; }
    "$data_check" "$data_dir" || { echo "required task data is missing" >&2; return 2; }
    local expected_revision actual_revision
    expected_revision="$(tr -d '[:space:]' < "$exp_root/SIDERIUS_REVISION")"
    [[ "$expected_revision" == "61d5e5b1bcb8d569cf9904aae904ffef312e28f6" ]] || { echo "unexpected SIDERIUS_REVISION" >&2; return 2; }
    actual_revision="$(git -C "$siderius_checkout" rev-parse HEAD 2>/dev/null)" || { echo "cannot inspect SIDERIUS checkout" >&2; return 2; }
    [[ "$actual_revision" == "$expected_revision" ]] || { echo "Siderius checkout revision mismatch" >&2; return 2; }
    [[ -f "$siderius_checkout/scripts/launch/run_chain.sh" && -f "$siderius_checkout/configs/llm/openai_tiered_pro.json" ]] || { echo "required SIDERIUS launch resources are missing" >&2; return 2; }
    [[ -f "$exp_root/$legacy_launcher" ]] || { echo "legacy launcher not found" >&2; return 2; }
    [[ -e "$workspace" ]] || mkdir -p "$workspace"
    workspace="$(cd "$workspace" && pwd -P)"
    mkdir -p "$workspace/generated_library"
    unset SIDERIUS_PLUGIN_DIRS AGENT_GENERATED_DIR SIDERIUS_MODEL_PLUGIN_PATH SIDERIUS_LOSS_PLUGIN_PATH SIDERIUS_LOSS_DIRS
    export SIDERIUS_GENERATED_LIBRARY_DIR="$workspace/generated_library"
    export SIDERIUS_CHAIN_WORKSPACE="$workspace"
    local -a args=(--siderius-checkout "$siderius_checkout" --workspace "$workspace" --data_dir "$data_dir" "${fixed_args[@]}" )
    [[ "$dry_run" == 1 ]] && args+=(--dry-run)
    exec bash "$exp_root/$legacy_launcher" "${args[@]}"
}
