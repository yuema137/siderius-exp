"""Read actual task scopes with the pinned infra resolver; never approximate counts."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, model_validator

if TYPE_CHECKING:
    from tutorials.paper.runner import TutorialExperiment


class TaskView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fingerprint: str
    train: tuple[str, ...]
    val: tuple[str, ...]
    example_counts: dict[str, int | None]

    @model_validator(mode="after")
    def independent_populations(self) -> TaskView:
        if not self.train or not self.val:
            raise ValueError("both train and validation must be nonempty")
        for keys in (self.train, self.val):
            if len(set(keys)) != len(keys):
                raise ValueError("duplicate curve identity in task scope")
        train_stars = {key.split(":")[0] for key in self.train}
        val_stars = {key.split(":")[0] for key in self.val}
        if train_stars & val_stars:
            raise ValueError("a star appears in both train and validation")
        return self

    def populations(self) -> dict[str, set[str]]:
        return {"train": set(self.train), "val": set(self.val)}


_SCOPE_SCRIPT = """
import json, sys
from workflows.task_composition import compose_run_task_bindings
from execute_tools.task_data_path import ScopeBuildRequest
c = compose_run_task_bindings(sys.argv[1])
p = c.task_data_path
if p.task_data_path_id != 'phyts_tess_rotation':
    raise ValueError('this tutorial supports the TESS task data path only')
fractions = json.loads(sys.argv[2])
def scope(kind, split, portion):
    request = ScopeBuildRequest(round_kind=kind, selection_strategy='snapshot',
                                portion=portion, seed=42)
    return (p.build_training_scope if split == 'train' else p.build_eval_scope)(request)
counts = {}
for name, portion in fractions.items():
    kind, split = name.split('_')
    counts[name] = None if portion is None else len(scope(kind, split, portion).keys)
print(json.dumps(dict(fingerprint=c.semantic_fingerprint,
    train=scope('trial', 'train', 1.0).keys,
    val=scope('trial', 'val', 1.0).keys, example_counts=counts)))
"""


def inspect_task(experiment: TutorialExperiment) -> TaskView:
    """Seed-42 examples; actual attempt seeds may choose different whole-star groups."""
    from tutorials.paper.runner import child_environment

    if experiment.composition is None:
        raise ValueError("select a task composition before inspecting its populations")
    fractions = {
        "trial_train": experiment.trial_train_fraction,
        "trial_val": experiment.trial_val_fraction,
        "formal_train": experiment.formal_train_fraction,
        "formal_val": experiment.formal_val_fraction,
    }
    result = subprocess.run(
        [
            str(experiment.infra_checkout / ".venv/bin/python"),
            "-B",
            "-c",
            _SCOPE_SCRIPT,
            str(experiment.composition),
            json.dumps(fractions),
        ],
        cwd=experiment.infra_checkout,
        env=child_environment(experiment),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.strip().splitlines()
    if not lines:
        raise ValueError("task inspection returned no scope evidence")
    return TaskView.model_validate_json(lines[-1])
