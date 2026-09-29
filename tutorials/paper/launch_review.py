"""Read saved tutorial inputs and render a launch checklist without execution."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Literal

import yaml
from workflows.llm_config import WorkflowLLMConfig

from tutorials.paper.runner import ROOT, TutorialExperiment, credential_status


def _binding(script: str, name: str) -> str:
    rows = [line for line in script.splitlines() if line.startswith(name + "=")]
    if len(rows) != 1:
        raise ValueError(f"launcher must contain exactly one {name}= assignment")
    values = shlex.split(rows[0].split("=", 1)[1])
    if len(values) != 1:
        raise ValueError(f"launcher {name} must be one literal path")
    return values[0]


def launch_review(
    config: Path, script: Path, *, task: Literal["tess", "tidmad"]
) -> str:
    """Re-read disk; show no launch command for mismatched or missing inputs.

    Presence checks are intentionally cheap. Native terminal preview/launch owns
    source pins, data integrity, composition, CUDA and credential admission.
    """
    if task not in ("tess", "tidmad"):
        raise ValueError("choose tess or tidmad")
    config, script = config.resolve(), script.resolve()
    missing = [p for p in (config, script) if not p.is_file()]
    if missing:
        return "**STOP — save your selected example first. Missing:**\n\n" + "\n".join(
            f"- `{p}`" for p in missing
        )
    if task == "tidmad":
        from tutorials.paper.tidmad.runner import (
            TidmadExperiment,
            selected_split,
        )
        from tutorials.paper.tidmad.runner import credential_status as tidmad_keys

        settings = TidmadExperiment.model_validate_json(config.read_text())
        keys = tidmad_keys(settings)
        module = "tutorials.paper.tidmad.runner"
    else:
        settings = TutorialExperiment.model_validate_json(config.read_text())
        keys = credential_status(settings.llm_config)
        module = "tutorials.paper.runner"
    text = script.read_text()
    if Path(_binding(text, "EXPERIMENT")).resolve() != config:
        raise ValueError("STOP: the script's EXPERIMENT points to a different JSON")
    if Path(_binding(text, "EXP_CHECKOUT")).resolve() != ROOT:
        raise ValueError("STOP: the script selects a different exp checkout")
    expected = f'exec "$EXP_CHECKOUT/.venv/bin/python" -B -m {module} --experiment "$EXPERIMENT" "$@"'
    if expected not in text.splitlines():
        raise ValueError(
            "STOP: this is not the selected task's tutorial search launcher"
        )
    if settings.composition is None or settings.llm_config is None:
        raise ValueError("select saved composition and llm_config paths")
    WorkflowLLMConfig.from_json(str(settings.llm_config))
    declaration = yaml.safe_load(settings.composition.read_text())
    rows = [
        (
            "1. Experiment JSON",
            config,
            "Review the parameter table below; this is what the script reads.",
        ),
        (
            "2. Task entry YAML",
            settings.composition,
            "Check that this is the task/split you meant to run.",
        ),
        (
            "3. LLM routing JSON",
            settings.llm_config,
            "Check provider/model choices. Never put API key values here.",
        ),
        (
            "4. Search shell script",
            script,
            "EXPERIMENT was checked against row 1; this is the file bash executes.",
        ),
    ]
    extra = ""
    if task == "tidmad":
        split = selected_split(settings)
        literature = (
            settings.composition.parent.parent / "framework_configs/lit_review.yaml"
        )
        rows.append(
            (
                "5. Literature-review config",
                literature,
                "Literature review is enabled in this workflow.",
            )
        )
        data_files = [
            settings.data_dir / f"abra_{family}_{i:04d}.h5"
            for family in ("training", "validation")
            for i in range(4)
        ]
        data_files.append(settings.data_dir / "segment_anchors.json")
        if split is not None:
            extra = f"**Saved file groups:** training `{list(split.train_files)}`; workflow validation `{list(split.validation_files)}`; final test `{list(split.test_files)}`. The search command below does not run final testing."
        else:
            extra = "**Saved protocol: paper-pool.** Formal training fraction `.1` means the complete frozen 20/200 parent pool; Trial fractions are within those 20 segments."
    else:
        manifest = (
            settings.composition.parent
            / declaration["task_data_path"]["config"]["manifest_path"]["ref"]
        ).resolve()
        rows.append(
            (
                "5. Split identity CSV",
                manifest,
                "Its split column owns train/val membership. A re-split needs the matching task AND NPZ pair.",
            )
        )
        data_files = [
            settings.data_dir / f"tess_rotation_{split}.npz"
            for split in ("train", "val")
        ]
        extra = "**Saved task split:** inspect the CSV in row 5. Data fractions below sample within that split; they do not change its membership."
    lines = [
        "### A. Check these saved files",
        "",
        "| Open this | Actual path | What to check |",
        "|---|---|---|",
    ]
    lines += [f"| {label} | `{path}` | {meaning} |" for label, path, meaning in rows]
    lines += [
        "",
        extra,
        "",
        "Human advice is **inactive** in this NoPrior workflow. No advice file is read.",
        "",
        "### B. Confirm the parameters read from the JSON",
        "",
        f"Source: `{config}`. These values were reloaded from disk, not from earlier notebook variables.",
        "",
        "| Parameter | Saved/effective value | Meaning |",
        "|---|---|---|",
    ]
    fields = [
        ("run_name", settings.run_name, "New run identity"),
        ("gpu", settings.gpu, "Must match the supported physical NVIDIA GPU"),
        ("iterations", settings.iterations, "Search-cycle ceiling"),
        ("epochs", settings.epochs, "Epoch ceiling per training attempt"),
        (
            "trial_train_fraction",
            settings.trial_train_fraction,
            "Trial training fraction; null leaves the native workflow to choose",
        ),
        (
            "trial_val_fraction",
            settings.trial_val_fraction,
            "Trial scoring fraction; null leaves the native workflow to choose",
        ),
        (
            "formal_train_fraction",
            settings.formal_train_fraction,
            "Formal training fraction; see paper-pool exception above if selected",
        ),
        (
            "formal_val_fraction",
            settings.formal_val_fraction,
            "Formal scoring fraction",
        ),
        ("trial_minutes", settings.trial_minutes, "Minutes per Trial training attempt"),
        (
            "formal_minutes",
            settings.formal_minutes,
            "Minutes per Formal training attempt",
        ),
        ("vram_gib", settings.vram_gib, "Shared model VRAM budget in GiB"),
        (
            "trial_vram_gib",
            settings.trial_vram_gib,
            f"Effective Trial budget: {settings.trial_vram_gib or settings.vram_gib} GiB; null uses vram_gib",
        ),
        (
            "formal_vram_gib",
            settings.formal_vram_gib,
            f"Effective Formal budget: {settings.formal_vram_gib or settings.vram_gib} GiB; null uses vram_gib",
        ),
    ]
    lines += [
        f"| `{name}` | `{value if value is not None else 'null'}` | {meaning} |"
        for name, value, meaning in fields
    ]
    lines += [
        "",
        "**If a value is wrong:** edit and save the JSON named above, then rerun this review cell. Editing an earlier Python variable alone does not update that JSON. Changing a split also requires its matching task/data preparation. Time budgets are per training attempt, not a total wall-time or API-cost cap.",
        "",
        "### C. Confirm inputs, outputs and credentials",
        "",
        f"**Input data directory:** `{settings.data_dir}`",
        "",
    ]
    lines += [
        f"- `{'FOUND' if p.is_file() else 'MISSING'}` — `{p}`" for p in data_files
    ]
    receipt = settings.workspace.with_name(settings.workspace.name + ".tutorial.json")
    lines += [
        "",
        f"**New output workspace:** `{settings.workspace}`",
        "",
        f"**Launch receipt:** `{receipt}`",
        "",
        "The output workspace must not already exist. For another run, save a new `workspace` and `run_name` in the experiment JSON.",
        "",
        "**Required environment variables (names only):** "
        + ", ".join(f"`{k}`" for k in keys),
        "",
        "Export these in the terminal that will launch the script. A key file merely existing is not enough. Kernel and terminal environments may differ; this notebook does not certify terminal credentials.",
        "",
    ]
    lines += [
        "**Notebook kernel presence (not the launching terminal):** "
        + ", ".join(
            f"`{name}`: {'present' if present else 'MISSING'}"
            for name, present in keys.items()
        ),
        "",
    ]
    if not all(keys.values()):
        lines += [
            "**Credential warning:** this kernel lacks required keys. Export them in the launching terminal and verify preview there; never paste values into notebook cells.",
            "",
        ]
    missing = [p for p in [*(row[1] for row in rows), *data_files] if not p.is_file()]
    if missing or settings.workspace.exists():
        lines += [
            "**STOP — no new launch command.** Prepare any missing inputs above. If the workspace already exists, keep this configuration to inspect its completed run (and, for TIDMAD file-holdout, select a final-test candidate). Only for a NEW search, save a fresh workspace/run_name and rerun this cell."
        ]
        return "\n".join(lines)
    preview = shlex.join(["bash", str(script)])
    lines += [
        "### D. Run these terminal commands in order",
        "",
        "The absolute paths work from any terminal directory. Keep the notebook open beside the terminal. These are displayed commands; this cell does not execute them.",
        "",
        "**1. Preview — copy this entire line into a terminal:**",
        "",
        f"```bash\n{preview}\n```",
        "",
        "Preview does not train or call the LLM. Check its `settings` against table B, its task/data/workspace paths against A/C, and its required key status. If preview errors, fix the error before continuing. It does not certify data hashes or CUDA; launch checks those.",
        "",
        "**2. After checking preview and exporting credentials in that same terminal, start the run — copy this entire line:**",
        "",
        f"```bash\n{preview} --launch\n```",
        "",
        f"This runs **`{script}`**, which reads **`{config}`**, selects **`{settings.composition}`**, and writes into **`{settings.workspace}`**. The `--launch` flag changes preview into paid API/GPU execution. You do not run the JSON, YAML, or notebook as the launch command.",
        "",
        "Keep the terminal open. Inspect the exit status and run records when it finishes; completion of a command is not proof of a scientifically valid model.",
    ]
    return "\n".join(lines)
