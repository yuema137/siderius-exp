#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 DATA_DIR INDEX_DIR OUTPUT_ROOT" >&2
  exit 2
fi

data_dir=$1
index_dir=$2
output_root=$3
python_bin="$(git rev-parse --show-toplevel)/.venv/bin/python"
revision=$(git rev-parse HEAD)

run_one() {
  local name=$1
  shift
  "$python_bin" -m tasks.supernemo_signal_background.tools.run_baseline \
    --data-dir "$data_dir" \
    --index-dir "$index_dir" \
    --output-dir "$output_root/${name}_${revision:0:7}" \
    "$@"
}

mkdir -p "$output_root"
run_one mlp_small \
  --architecture mlp --width 64 --depth 2 --batch-size 4096 \
  --train-per-process 100000 --validation-per-process 25000 --epochs 10
run_one mlp_large \
  --architecture mlp --width 1024 --depth 6 --batch-size 4096 \
  --train-per-process 100000 --validation-per-process 25000 --epochs 10
run_one cnn_small \
  --architecture cnn --width 128 --depth 3 --batch-size 1024 \
  --train-per-process 100000 --validation-per-process 25000 --epochs 10
run_one resnet_medium \
  --architecture resnet --width 256 --depth 4 --batch-size 512 \
  --train-per-process 100000 --validation-per-process 25000 --epochs 10
run_one resnet_large \
  --architecture resnet --width 1024 --depth 6 --batch-size 128 \
  --train-per-process 100000 --validation-per-process 25000 --epochs 10
