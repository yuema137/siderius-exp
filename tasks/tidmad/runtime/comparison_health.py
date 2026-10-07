"""Require the same scientific checks for runtime and production attribution."""

from typing import Any

from execute_tools.health_checks.config import (
    HealthChecksConfig,
    load_composed_health_config,
)


def validate_comparison_health(
    runtime_config: str | None, production_policy: str, task_binding: str
) -> None:
    """Refuse stale/custom science before training or relabelling old evidence.

    Runtime actions and cadence may be observation-only. Monitored file
    overrides select where the same check runs; they do not change its rule.
    Thresholds, check identities and aggregation must match because production
    attribution reuses the runtime result rather than evaluating it again.
    """
    production, _, _ = load_composed_health_config(production_policy, task_binding)
    runtime, _, _ = load_composed_health_config(runtime_config, task_binding)

    def scientific_checks(
        config: HealthChecksConfig,
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            gate.id: [
                {
                    "name": check.name,
                    "config": {
                        key: value
                        for key, value in check.config.items()
                        if key != "peek_file_indices"
                    },
                }
                for check in gate.checks
            ]
            for gate in config.health_gates
        }

    if scientific_checks(runtime) != scientific_checks(production):
        raise ValueError(
            "Comparison runtime Health checks differ from the selected task's "
            "production checks. Use matching task thresholds and check IDs in a "
            "new workspace; do not reinterpret an old effective configuration. "
            "Observation-only actions and monitored-file overrides are supported."
        )
