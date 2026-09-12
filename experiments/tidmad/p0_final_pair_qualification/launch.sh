#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/p0_final_pair_qualification/common.sh"
tidmad_check() { [[ -f "$1/abra_training_0004.h5" && -f "$1/abra_validation_0004.h5" ]]; }
export SIDERIUS_PREFLIGHT_WORKER_MEM_GIB=24 SIDERIUS_SUBPROCESS_RSS_GB='training=40,inference=60,scoring=24'
TIDMAD_ARGS=(--formal_round_strategy full_clone --workflow_parameter_rules '{"train_config.epochs":{"exact":1},"train_config.batch_size":{"exact":16}}' --validation_max_train_samples 1024 --validation_max_samples 1024 --vram_probe_step_timeout_seconds 60 --vram_preflight_total_timeout_seconds 240)
p0_qualification_main tidmad experiments/tidmad/two_iteration_qualification/launch.sh tidmad_check "${TIDMAD_ARGS[@]}" \
  --run_name tidmad_p0_final --force_fresh --no_auto_resume --no-runtime_watchdog --no-ml_lit_review_enabled --num_iterations 2 --max_rounds 2 --max_epochs 1 --trial_max_epochs 1 --formal_max_epochs 1 \
  --trial_portion .01 --train_portion 1 --eval_portion .01 --formal_portion .01 --formal_train_portion 1 --formal_eval_portion .01 \
  --data_scope 4 --health_gate_files 4 --sampling_seed 20260912 --plan_overrides '{"is_trial":true,"trial_strategy":"snapshot","eval_strategy":"snapshot","train_validation_align":true}' \
  --formal_strategy snapshot --force_formal_round --attempts_per_round 2 --attempts_per_formal_round 2 --max_fail_rounds 1 --max_failed_iterations 2 --max_proposal_attempts 2 --max_impl_attempts 2 --min_formal_batch_size 1 --max_steps_per_attempt 1024 --trial_time_budget_minutes 3 --formal_time_budget_minutes 5 --runtime_verification_max_wall_seconds 120 --trial_vram_budget_gb 8 --formal_vram_budget_gb 12 --no-ml_lit_review_enabled --no-cleanup_denoised -- "$@"
