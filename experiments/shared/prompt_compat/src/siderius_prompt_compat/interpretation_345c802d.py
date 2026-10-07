"""Frozen historical rendering only; see source-inventory.json for provenance."""

import json

from typing import TYPE_CHECKING, Any

from agent.schemas.health_feedback import CollapseFingerprint

from agent.schemas.interpretation import ModelRunSummary

from agent.schemas.score_table import ScoreComparisonTable

from execute_tools.metric_order import MetricOrder

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agent.schemas.interpretation import (
        InterpretationInput,
        InterpretationTaskBlocks,
        MetricIdentity,
        RecordFailureCounts,
        SecondaryMetricEvidence,
    )
    from agent.schemas.proposal import VocabEntry
    from agent.schemas.training_diagnosis import TrainingDiagnosis

PER_MODEL_SYSTEM_PROMPT = """\
You are a senior ML research analyst.

Your task: analyse the tuning run summary for ONE model architecture and produce a
structured analysis covering performance, per-sample behaviour where per-sample
evidence exists, data sensitivity, training dynamics, efficiency, and strategy
assessment. The research context is:

{TASK_DESCRIPTION}

You will receive:
- The model's architectural description (markdown + math)
- Best and worst golden-metric scores (trial best and formal score if available)
- Best configuration
- Score trajectory across rounds (with trial portions and model sizes)
- Per-round conclusions from the tuning agent's reflections

{TASK_GUIDANCE_SECTIONS}
Produce a JSON object with exactly these fields:

{
  "key_findings": [
    "Most important finding — concrete, references actual scores and configs",
    ...
  ],
  "bottlenecks": [
    "Root cause preventing further improvement for this specific model",
    ...
  ],
  "best_config_analysis": "Why the best config worked — what made it better than others",
  "score_trend": "How scores evolved across rounds — improving, plateauing, or erratic",
  "per_file_analysis": "Per-sample behaviour analysis. When the summary includes per-sample evidence (a score table), analyse it following the task guidance; when it does not, state explicitly that no per-sample evidence is available — never invent per-sample claims.",
  "data_sensitivity": "How sensitive the model is to data volume. Did scores improve when trial_portion increased? How large is the trial-vs-formal gap?",
  "efficiency_assessment": "Model parameter count vs performance. Is there a simpler config with similar score? Cost-performance tradeoff.",
  "strategy_assessment": "Did the agent explore effectively? Did it increase data when needed? Did it follow screening→refinement→solidification phases?"
}

Rules:
- key_findings: ranked by importance, evidence-based, reference actual values
- bottlenecks: root causes (e.g. 'architecture capacity ceiling'), not symptoms
- best_config_analysis: be specific about which hyperparameters mattered most
- score_trend: identify whether the model has saturated or still has room to improve
- per_file_analysis: follow the task guidance when per-sample evidence is present; otherwise state its absence
- data_sensitivity: reference the training data volume and trial_portion changes across rounds
- efficiency_assessment: reference model_params and training times if available
- strategy_assessment: comment on whether the agent's exploration strategy was effective
- Output only the JSON object — no preamble, no commentary, no markdown
"""

_TASK_SECTION_HEADERS = {
    "evidence_reading": "Task evidence guidance",
    "per_model_guidance": "Task analysis guidance (per-model)",
    "synthesis_guidance": "Task synthesis guidance",
    "prediction_guidance": "Task prediction guidance",
}

_PER_MODEL_SECTIONS = ("evidence_reading", "per_model_guidance")

def _render_task_sections(blocks: "InterpretationTaskBlocks | None", names: tuple[str, ...]) -> str:
    """The framework-owned splice: selected sections, in framework order.

    An ABSENT section renders NOTHING — no header, no bytes (absence of
    guidance is legal, frozen 09b §4.1). Present prose is preserved verbatim
    except for outer-edge whitespace, which the splice normalises so every
    section is framed identically regardless of how the declaration file's
    block scalars terminate.
    """
    if blocks is None:
        return ""
    parts: list[str] = []
    for name in names:
        content: str | None = getattr(blocks, name)
        if content is None:
            continue
        parts.append(f"### {_TASK_SECTION_HEADERS[name]}\n\n{content.strip()}\n\n")
    return "".join(parts)

def _build_per_model_system_prompt(inp: "InterpretationInput") -> str:
    """Assemble the Phase-1 system prompt: framework template + task values.

    Substitutes the ``{TASK_DESCRIPTION}`` placeholder from
    ``inp.task_description`` (T4b — see
    docs/design/enable_global_task_config.md § Commit T4) and splices the
    caller-supplied ``inp.task_blocks`` sections (Step 09b C2:
    ``evidence_reading`` + ``per_model_guidance``) at the framework's
    ``{TASK_GUIDANCE_SECTIONS}`` slot. ``task_blocks=None`` renders the bare
    task-free template — no section, no header.

    Production callers always populate ``inp.task_description`` via the
    workflow; test fixtures may leave it at the default ``""``, in which case
    the placeholder collapses to ``""`` (acceptable for tests, never reached
    in production).
    """
    rendered = PER_MODEL_SYSTEM_PROMPT.replace("{TASK_DESCRIPTION}", inp.task_description)
    rendered = rendered.replace(
        "{TASK_GUIDANCE_SECTIONS}\n",
        _render_task_sections(inp.task_blocks, _PER_MODEL_SECTIONS),
    )
    # V19 PR 3 §3.6 item 3 (flag-gated): instruction block for handling the
    # structured HealthGate evidence. OFF ⇒ byte-identical to the flag-less
    # assembly (golden-parity tested).
    if inp.enable_structured_health_feedback:
        rendered += HEALTH_FEEDBACK_SYSTEM_INSTRUCTIONS
    return rendered

HEALTH_FEEDBACK_SYSTEM_INSTRUCTIONS = """

### Structured HealthGate evidence (additional rules)

The user prompt may contain a "HealthGate summary" section and per-round
GATE labels. These are DETERMINISTIC facts from the health-gate system,
not opinions. Rules:

- Preserve every collapse fingerprint VERBATIM in your findings — the
  exact signature string with its numbers (e.g.
  "sample_dispersion_floor_blocking:dispersion=0.0"). Never paraphrase
  the numbers away.
- A high raw score on a round with invalid gate evidence is an INVALID
  result. Report it as a failure mode, never as an achievement.
- Rounds marked "unknown" or with legacy/no gate evidence carry NO
  health verdict. Do not describe them as healthy or collapsed.
- Attribute each fingerprint to exactly the model and rounds it came
  from. Never transfer evidence between models."""

def _render_health_summary_section(summary: ModelRunSummary, *, order: MetricOrder) -> list[str]:
    """Deterministic ``### HealthGate summary`` body (V19 PR 3 §3.6 item 2).

    Reads ONLY the ``round_health`` data — never LLM prose. Returns [] when
    every round is legacy/unknown with nothing to report, so the caller can
    skip the header entirely.

    ``order`` (Step 09a C3) picks the BEST-SCORING round whose recording
    diagnostics are rendered. That selection is a direction question: under a
    lower-is-better metric the old ``s > best_score`` literal would surface the
    WORST round's diagnostics while calling them the best round's.
    """
    counts = {"valid": 0, "invalid": 0, "unknown": 0}
    fingerprint_rounds: dict[str, list[int]] = {}
    fingerprint_by_sig: dict[str, CollapseFingerprint] = {}
    for i, health in enumerate(summary.round_health):
        counts[str(health.health_validity)] += 1
        if health.fingerprint is not None:
            sig = health.fingerprint.signature
            fingerprint_rounds.setdefault(sig, []).append(i + 1)
            fingerprint_by_sig.setdefault(sig, health.fingerprint)

    lines = [
        f"Round validity: {counts['valid']} valid, {counts['invalid']} invalid, "
        f"{counts['unknown']} unknown (of {len(summary.round_health)})"
    ]
    for index, health in enumerate(summary.round_health, start=1):
        for outcome in health.gate_outcomes:
            if outcome.check_passed is False:
                lines.append(
                    f"  Round {index} check {outcome.gate_name}: failed; "
                    f"configured_action={outcome.configured_action or 'unknown'}; "
                    f"resolved_action={outcome.resolved_action or 'unknown'}; "
                    f"would_invalidate={outcome.would_invalidate_under_production_policy}; "
                    f"round_validity={health.health_validity}. "
                    "A failed diagnostic is not by itself candidate invalidity."
                )
    if fingerprint_rounds:
        lines.append(
            "Distinct collapse fingerprints (deterministic, from persisted gate evidence):"
        )
        for sig in sorted(fingerprint_rounds):
            rounds = fingerprint_rounds[sig]
            fp = fingerprint_by_sig[sig]
            lines.append(
                f"  - {sig}  (x{len(rounds)}, round{'s' if len(rounds) > 1 else ''} "
                f"{', '.join(str(r) for r in rounds)}) — {fp.human_readable}"
            )

    # Recording-only diagnostics for the best-scoring round, if any round
    # carries them (e.g. pearson_dispersion — the misleading-high-score
    # discriminator, design §2.4).
    best_idx = None
    best_score = None
    for i, s in enumerate(summary.round_scores):
        if s is not None and (best_score is None or order.is_better(s, best_score)):
            best_idx, best_score = i, s
    if best_idx is not None and best_idx < len(summary.round_health):
        recording = {
            k: v
            for outcome in summary.round_health[best_idx].gate_outcomes
            if outcome.configured_action == "continue"
            for k, v in outcome.key_metrics.items()
        }
        if recording:
            rendered = ", ".join(f"{k}={v}" for k, v in sorted(recording.items()))
            lines.append(f"Best-round recording diagnostics: {rendered}")

    if counts["invalid"] == 0 and counts["valid"] == 0 and not fingerprint_rounds:
        # All-unknown/legacy with no fingerprints: nothing informative.
        return []
    return lines

def render_metric_identity(identity: "MetricIdentity | None") -> str | None:
    """``golden metric `<id>` (<higher|lower> is better)`` — or None.

    Step 09b C3. The DIRECTION WORDS come from the existing 07b authority
    (:func:`agent.prompt_templates.tuner.rendering.render_metric_direction_words`,
    which asks `MetricOrder`), never from a literal spelled here: the
    direction vocabulary is interpreted in exactly one module, and a second
    renderer deciding "higher"/"lower" itself is the pattern Step 09 removed.

    The 07b line renderer itself takes a ``MetricSpec`` and reads ``spec.id``;
    a ``MetricIdentity`` names that field ``metric_id`` (it is the RECORD-borne
    identity, not the declaration), so this composes the same sentence around
    the shared direction words rather than adapting one carrier into the other.

    ``None`` (a summary carrying no record-borne identity — pre-Step-06
    outputs) renders NOTHING: the run-level identity line still states the
    metric, so a per-model absence is silent rather than fabricated.
    """
    if identity is None:
        return None
    from agent.prompt_templates.tuner.rendering import render_metric_direction_words

    words = render_metric_direction_words(identity)
    return f"golden metric `{identity.metric_id}` ({words['comparative']} is better)"

def render_interpretation_diagnosis_lines(
    best: "TrainingDiagnosis | None", formal: "TrainingDiagnosis | None"
) -> list[str]:
    """Up to two role-labelled training-dynamics lines for one model.

    Step 09b C3. The LINE GRAMMAR is 07b's
    (:func:`agent.prompt_templates.tuner.rendering.render_training_dynamics_line`),
    reused verbatim — including its explicit degenerate renderings ("training
    dynamics: none recorded" / "invalid (non-finite)"), because a silent
    omission reads to the model as "training was unremarkable".

    The two roles are rendered SEPARATELY on purpose (09a C6): a best trial
    round and the formal round are different experiments, and folding them
    would attribute one experiment's dynamics to the other. A role whose
    diagnosis is absent contributes NO line — the run may legitimately have
    no formal round — but a PRESENT diagnosis always renders, degenerate or
    not.

    ``objective_kind`` is deliberately not passed: the interpreter receives
    the projected diagnosis alone (no `training_history` reaches the
    summary), which is exactly the reflector's situation in 07b.
    """
    from agent.prompt_templates.tuner.rendering import render_training_dynamics_line

    lines: list[str] = []
    for role, diagnosis in (("best", best), ("formal", formal)):
        if diagnosis is None:
            continue
        lines.append(f"  {role}: {render_training_dynamics_line(diagnosis, None)}")
    return lines

def render_secondary_metrics(secondaries: "Sequence[SecondaryMetricEvidence]") -> list[str]:
    """One line per DECLARED secondary metric, in declaration order.

    Step 09b C3 (parent §4b; Q-09-7 = B). Secondaries are OBSERVATIONAL: each
    line states the metric's OWN identity and OWN direction — asked of its own
    `MetricOrder`, never of the run's — and none of them is ever compared,
    ranked or aggregated here.

    The three states are rendered as three DIFFERENT statements, because they
    are three different facts:

    * ``scored``      -> the value;
    * ``refused``     -> the refusal's contract id, verbatim and unparsed;
    * ``unavailable`` -> a NAMED ABSENCE ("declared, not evaluated this run").

    An empty collection renders NOTHING (production today — Step 10 owns the
    upstream transport), so no header is emitted for a task that declares no
    secondary metric.
    """
    from agent.prompt_templates.tuner.rendering import render_metric_direction_words

    lines: list[str] = []
    for evidence in secondaries:
        words = render_metric_direction_words(evidence.spec)
        head = f"  `{evidence.spec.id}` ({words['comparative']} is better): "
        status = evidence.status
        if status == "scored":
            assert evidence.result is not None  # narrowed by `status`
            lines.append(f"{head}{evidence.result.scalar}")
        elif status == "refused":
            assert evidence.refusal is not None  # narrowed by `status`
            lines.append(f"{head}not scoreable ({evidence.refusal.verdict.contract_id})")
        else:
            lines.append(f"{head}declared, not evaluated this run")
    return lines

def render_failure_counts(counts: "RecordFailureCounts | None") -> list[str]:
    """What went wrong across one model's records, from EXISTING vocabularies.

    Step 09b C3 (parent §5). Every key comes from an authority that already
    owns it — `ExperimentRecord.status`, `TrainingDiagnosis.state`,
    `ValidationState`, `NotScoreableResult`'s contract ids, Health
    `gate_action` / `RoundHealth.provenance`. No new failure taxonomy is
    introduced, and an unknown FUTURE key renders verbatim under its own name
    because these are open dicts, not enums.

    Zero-valued and empty groups are omitted (a zero count is not evidence);
    ``None`` renders nothing at all — a cached model that carries no stored
    counts is ABSENT, never reported as "no failures".
    """
    if counts is None:
        return []

    def _group(label: str, mapping: dict[str, int]) -> str | None:
        present = {k: v for k, v in mapping.items() if v}
        if not present:
            return None
        rendered = ", ".join(f"{k}={v}" for k, v in sorted(present.items()))
        return f"  {label}: {rendered}"

    lines: list[str] = [f"  records: {counts.records_total}"]
    for label, mapping in (
        ("status", counts.status_counts),
        ("training diagnosis", counts.diagnosis_state_counts),
        ("validation", counts.validation_state_counts),
        ("gate actions", counts.gate_action_counts),
        ("health provenance", counts.health_provenance_counts),
    ):
        line = _group(label, mapping)
        if line is not None:
            lines.append(line)
    if counts.metric_refusal_count:
        refusals = ", ".join(f"{k}={v}" for k, v in sorted(counts.refusal_contract_ids.items()))
        suffix = f" ({refusals})" if refusals else ""
        lines.append(f"  metric refusals: {counts.metric_refusal_count}{suffix}")
    return lines

def _build_per_model_prompt(
    summary: ModelRunSummary,
    description: str | None,
    expert_advice_str: str = "",
    human_advice: str | None = None,
    *,
    structured_health_feedback: bool = False,
    order: MetricOrder | None = None,
) -> str:
    """Build the user prompt for a single model's summarization.

    ``structured_health_feedback`` (V19 PR 3 §3.6) gates the structured
    HealthGate additions — the trajectory gate labels and the
    ``### HealthGate summary`` section. OFF (default): output is
    byte-identical to the pre-PR3 prompt, proven by golden-file equality
    in ``test_health_prompt_parity.py`` — every PR 3 addition below must
    stay behind this flag.

    ``order`` (Step 09a C3) is needed ONLY by that flag-ON section, which
    picks a best-scoring round. It therefore keeps a ``None`` default so every
    flag-OFF caller and every prompt golden is untouched — and raises when the
    flag is ON without it, rather than rendering a round chosen by an assumed
    direction.
    """
    if structured_health_feedback and order is None:
        raise ValueError(
            "structured_health_feedback=True renders the best-scoring round's "
            "diagnostics, which requires the run's MetricOrder. Pass order=; the "
            "direction is never assumed."
        )
    lines = [
        f"## Model: {summary.model_type}",
        f"Run: {summary.run_name} | Status: {summary.status} | Rounds: {summary.completed_rounds}",
    ]
    # Step 09b C3 — what the scores below ARE and which way is better, stated
    # beside the D1 field labels rather than replacing them (the 07b Q-07b-3
    # precedent: the LLM reads `denoising_score` out of the record, and the
    # identity line says what that field measures).
    identity_line = render_metric_identity(summary.metric_identity)
    if identity_line is not None:
        lines.append(f"Metric               : {identity_line}")
    lines += [
        f"Raw best score       : {summary.best_denoising_score} "
        f"(health={summary.best_raw_health_validity})",
        f"Best valid score     : {summary.best_valid_denoising_score}",
        f"Worst denoising score: {summary.worst_denoising_score}",
    ]

    # Formal score (if available and distinct from best)
    if summary.formal_score is not None:
        lines.append(f"Formal round score   : {summary.formal_score}")

    # F-SCANE-4 — the ONE per-model headline that is BOTH HealthGate-valid AND
    # formal. Every other number above is mixed on one axis or the other:
    # `Raw best` and `Best valid` may come from a trial round, `Formal round
    # score` may come from a health-INVALID record. Before this line
    # `ModelRunSummary.best_valid_formal_score` had no production consumer past
    # its own construction, so the honest headline was persisted and rendered
    # nowhere while the mixed ones were rendered to the model.
    #
    # The ABSENCE is rendered too, and deliberately: "this model produced no
    # HealthGate-valid formal result" is the fact that matters most when it
    # holds, and omitting the line lets the mixed numbers above stand
    # unqualified — which is the shape of the defect, not a tidier prompt.
    if summary.best_valid_formal_score is not None:
        lines.append(f"Best valid formal    : {summary.best_valid_formal_score}")
    else:
        lines.append(
            "Best valid formal    : NONE — this model produced no "
            "HealthGate-valid formal result; every score above is from a "
            "trial round, a health-invalid record, or both."
        )

    # Model efficiency
    if summary.best_model_params is not None:
        lines.append(f"Best model params    : {summary.best_model_params:,}")

    # Data volume context. The label is the schema-derived record vocabulary
    # (`training_psd_segments`, presence-gated); the baseline-volume FACT that
    # used to ride here as a parenthetical is task science and lives in the
    # task's evidence_reading block since Step 09b C2 (design §22.2 DW-8).
    if summary.training_psd_segments is not None:
        lines.append(f"Training PSD segments: {summary.training_psd_segments}")
    if summary.eval_psd_segments is not None:
        lines.append(f"Eval PSD segments    : {summary.eval_psd_segments}")
    if summary.trial_portion is not None:
        lines.append(f"Trial portion (best) : {summary.trial_portion}")

    # Step 09b C3 — the deterministic evidence 09a projected onto the summary,
    # each family rendered by ONE authority and each section presence-gated
    # (an absent family emits no header, never a fabricated "none observed").
    diagnosis_lines = render_interpretation_diagnosis_lines(
        summary.best_training_diagnosis, summary.formal_training_diagnosis
    )
    if diagnosis_lines:
        lines += ["", "### Training dynamics", *diagnosis_lines]

    secondary_lines = render_secondary_metrics(summary.secondary_metrics)
    if secondary_lines:
        lines += [
            "",
            "### Secondary metrics (observational — never used for ranking)",
            *secondary_lines,
        ]

    failure_lines = render_failure_counts(summary.failure_counts)
    if failure_lines:
        lines += ["", "### Record outcomes", *failure_lines]

    if description:
        lines += ["", "### Architecture Description", description]
    lines += [
        "",
        "### Best Config",
        json.dumps(summary.best_config, indent=2) if summary.best_config else "none",
    ]

    # Per-file performance — rendered as the full ScoreComparisonTable
    # markdown (raw_baseline / ground_truth / model columns + subset-scoped
    # aggregates + Recovery line). Single source of truth lives on the
    # table.rendered_markdown field, produced by render_comparison_table.
    if summary.best_score_table is not None:
        lines += [
            "",
            "### Per-file performance (best experiment)",
            summary.best_score_table.rendered_markdown,
        ]

    if summary.formal_score_table is not None:
        lines += [
            "",
            "### Per-file performance (formal round — definitive)",
            summary.formal_score_table.rendered_markdown,
        ]
    elif summary.formal_file_vector is not None:
        # F-SCANE-4 — `formal_file_vector` is declared "Definitive per-file
        # performance" and had NO consumer of any kind, while the MIXED
        # `best_file_vector` was consumed. Its enriched twin above covers the
        # case where one exists; the enriched table is built from TIDMAD
        # reference science that a COMPOSED run deliberately omits
        # (F-12e-UX-7), so on those runs the definitive per-sample evidence
        # existed on the summary and reached nothing at all. Rendered as the
        # raw vector, and only where the richer view is genuinely absent.
        lines += [
            "",
            "### Per-sample performance (formal round — definitive, no enriched table)",
            json.dumps(summary.formal_file_vector),
        ]

    # Score trajectory with per-round trial portions and model params
    lines += ["", "### Score Trajectory (chronological)"]

    n_rounds = len(summary.round_scores)
    for i in range(n_rounds):
        score = summary.round_scores[i] if i < len(summary.round_scores) else None
        conclusion = summary.round_conclusions[i] if i < len(summary.round_conclusions) else ""
        trial_p = (
            summary.round_trial_portions[i]
            if summary.round_trial_portions and i < len(summary.round_trial_portions)
            else None
        )
        params = (
            summary.round_model_params[i]
            if summary.round_model_params and i < len(summary.round_model_params)
            else None
        )

        score_str = f"{score:.4f}" if score is not None else "skipped"
        extras = []
        if trial_p is not None:
            extras.append(f"portion={trial_p}")
        if params is not None:
            extras.append(f"params={params:,}")
        extra_str = f" [{', '.join(extras)}]" if extras else ""

        # V19 PR 3 §3.6 item 1 (flag-gated): label gate-invalidated rounds
        # with the resolved action and the deterministic collapse identity,
        # instead of the ambiguous bare "skipped".
        gate_str = ""
        if structured_health_feedback and i < len(summary.round_health):
            health = summary.round_health[i]
            if health.gate_action is not None and health.gate_action != "continue":
                cause = (
                    health.fingerprint.signature
                    if health.fingerprint is not None
                    else (health.failure_reason or "no persisted gate detail")
                )
                if score is None:
                    score_str = "invalidated"
                gate_str = f" [GATE {health.gate_action} — {cause}]"

        lines.append(f"  Round {i + 1}: score={score_str}{extra_str}{gate_str} — {conclusion}")

    # V19 PR 3 §3.6 item 2 (flag-gated): per-model HealthGate summary —
    # validity counts, distinct fingerprints with occurrence counts and
    # round indices, and recording-only diagnostics for the best round.
    # Rendered ONLY when there is something to say (no empty headers).
    # `order is not None` is guaranteed by the guard at the top of this
    # function whenever the flag is on; restating it here is what lets a type
    # checker see the narrowing, and it can never change behaviour.
    if structured_health_feedback and order is not None and summary.round_health:
        health_lines = _render_health_summary_section(summary, order=order)
        if health_lines:
            lines += ["", "### HealthGate summary", *health_lines]

    if expert_advice_str:
        lines += [
            "",
            "---",
            "## Expert Guidance",
            expert_advice_str,
        ]

    if human_advice:
        lines += [
            "",
            "---",
            "## Human Guidance (highest priority — overrides expert advice)",
            human_advice,
        ]

    return "\n".join(lines)
