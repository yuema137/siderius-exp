#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/p0_final_pair_qualification/common.sh"
davis_check() { [[ -d "$1/DAVIS/JPEGImages/480p" ]]; }
export SIDERIUS_PREFLIGHT_WORKER_MEM_GIB=32 SIDERIUS_SUBPROCESS_RSS_GB='training=40,inference=60,scoring=24'
DAVIS_ARGS=(--formal_round_strategy full_clone --workflow_parameter_rules '{"train_config.epochs":{"exact":1},"train_config.batch_size":{"exact":1}}' --validation_max_train_samples 3 --validation_max_samples 3 --vram_probe_step_timeout_seconds 60 --vram_preflight_total_timeout_seconds 240)
p0_qualification_main davis_future_prediction experiments/davis_future_prediction/two_iteration_qualification/launch.sh davis_check "${DAVIS_ARGS[@]}" \
  --run_name davis_p0_final --force_fresh --no_auto_resume --no-runtime_watchdog --no-ml_lit_review_enabled --num_iterations 2 --max_rounds 2 --max_epochs 1 --trial_max_epochs 1 --formal_max_epochs 1 \
  --trial_portion .05 --train_portion 1 --eval_portion .20 --formal_portion .05 --formal_train_portion 1 --formal_eval_portion .20 \
  --sampling_seed 20260912 --plan_overrides '{"is_trial":true,"trial_strategy":"snapshot","eval_strategy":"snapshot","train_validation_align":true}' \
  --formal_strategy snapshot --force_formal_round --attempts_per_round 2 --attempts_per_formal_round 2 --max_fail_rounds 1 --max_failed_iterations 2 --max_proposal_attempts 2 --max_impl_attempts 2 --min_formal_batch_size 1 --max_steps_per_attempt 3 --trial_time_budget_minutes 2 --formal_time_budget_minutes 3 --runtime_verification_max_wall_seconds 120 --trial_vram_budget_gb 10 --formal_vram_budget_gb 16 --vram_preflight_host_memory_limit_gb 32 --no-cleanup_denoised -- "$@"
