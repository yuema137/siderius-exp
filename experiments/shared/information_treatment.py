"""Resolve one experiment-owned information treatment for any adapter.

This module owns treatment presence and identity, not advice content. SIDERIUS
remains the authority for its advice JSON format and per-node routing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdviceMode(StrEnum):
    """Whether a frozen human-advice artifact belongs to the treatment."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class ModuleState(StrEnum):
    """Adapter-specific state of a named workflow module."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    NOT_APPLICABLE = "not_applicable"


class AdviceTreatment(BaseModel):
    """Identity of the single optional human-advice artifact."""

    model_config = ConfigDict(extra="forbid")

    mode: AdviceMode
    artifact: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    content_type: Literal["application/json"] | None = None

    @model_validator(mode="after")
    def require_coherent_identity(self) -> AdviceTreatment:
        if self.mode is AdviceMode.ENABLED and (
            self.artifact is None or self.sha256 is None or self.content_type is None
        ):
            raise ValueError("enabled advice requires artifact, sha256, and content_type")
        if self.mode is AdviceMode.DISABLED and (
            self.artifact is not None or self.sha256 is not None or self.content_type is not None
        ):
            raise ValueError("disabled advice requires null artifact, sha256, and content_type")
        return self


class InformationTreatment(BaseModel):
    """Portable declaration of information supplied to experiment adapters."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["siderius-exp-information-treatment-v1"]
    treatment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    task_package: str
    advice: AdviceTreatment
    modules: dict[str, dict[str, ModuleState]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_named_modules_and_adapters(self) -> InformationTreatment:
        for module, adapters in self.modules.items():
            if not module.strip():
                raise ValueError("module names must not be blank")
            if not adapters:
                raise ValueError(f"module {module!r} must declare at least one adapter state")
            if any(not adapter.strip() for adapter in adapters):
                raise ValueError(f"module {module!r} contains a blank adapter name")
        return self


class ResolvedInformationTreatment(BaseModel):
    """Validated treatment plus resolved repository-owned paths and identities."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    declaration: InformationTreatment
    manifest_path: Path
    manifest_sha256: str
    repository_root: Path
    task_package_path: Path
    advice_path: Path | None
    adapter: str
    module_states: dict[str, ModuleState]

    def siderius_args(self) -> list[str]:
        """Render existing public SIDERIUS arguments for the declared treatment."""

        if self.adapter != "siderius":
            raise ValueError(f"cannot render SIDERIUS arguments for adapter {self.adapter!r}")

        arguments = ["--experiment_arm", self.declaration.treatment_id]
        module_flags = {
            "literature_review": {
                ModuleState.ENABLED: "--ml_lit_review_enabled",
                ModuleState.DISABLED: "--no-ml_lit_review_enabled",
            }
        }
        for module, state in sorted(self.module_states.items()):
            try:
                arguments.append(module_flags[module][state])
            except KeyError as exc:
                raise ValueError(
                    f"module {module!r} state {state.value!r} cannot be represented "
                    "by the SIDERIUS adapter"
                ) from exc

        if self.declaration.advice.mode is AdviceMode.DISABLED:
            return arguments
        assert self.advice_path is not None
        assert self.declaration.advice.sha256 is not None
        arguments.extend(
            [
                "--advice",
                str(self.advice_path),
                "--advice_sha256",
                self.declaration.advice.sha256,
            ]
        )
        return arguments

    def receipt(self) -> dict[str, object]:
        """Return a path-portable record suitable for a frozen input bundle."""

        advice = self.declaration.advice
        return {
            "version": self.declaration.version,
            "treatment_id": self.declaration.treatment_id,
            "manifest_sha256": self.manifest_sha256,
            "task_package": self.declaration.task_package,
            "advice": {
                "mode": advice.mode.value,
                "artifact": "advice.json" if advice.mode is AdviceMode.ENABLED else None,
                "sha256": advice.sha256,
                "content_type": advice.content_type,
            },
            "adapter": self.adapter,
            "modules": {name: state.value for name, state in sorted(self.module_states.items())},
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repository_path(root: Path, raw: str, *, kind: str) -> Path:
    """Resolve a portable repository-relative path without allowing escape."""

    relative = PurePosixPath(raw)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"{kind} must be a repository-relative path without '..': {raw!r}")
    if "\n" in raw or "\r" in raw:
        raise ValueError(f"{kind} must not contain a newline")
    candidate = (root / Path(*relative.parts)).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"{kind} escapes the repository: {raw!r}")
    return candidate


def resolve_information_treatment(
    manifest_path: Path,
    *,
    repository_root: Path,
    adapter: str,
    required_modules: tuple[str, ...] = (),
) -> ResolvedInformationTreatment:
    """Load, certify, and resolve one information treatment for an adapter."""

    root = repository_root.resolve()
    manifest = manifest_path.resolve()
    if not manifest.is_file():
        raise FileNotFoundError(f"information treatment does not exist: {manifest}")
    try:
        raw = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid information treatment YAML at {manifest}: {exc}") from exc
    declaration = InformationTreatment.model_validate(raw)

    task_package = _repository_path(root, declaration.task_package, kind="task_package")
    if not task_package.is_dir():
        raise FileNotFoundError(f"declared task package is not a directory: {task_package}")

    advice_path: Path | None = None
    if declaration.advice.mode is AdviceMode.ENABLED:
        assert declaration.advice.artifact is not None
        assert declaration.advice.sha256 is not None
        advice_path = _repository_path(root, declaration.advice.artifact, kind="advice artifact")
        if not advice_path.is_file():
            raise FileNotFoundError(f"declared advice artifact does not exist: {advice_path}")
        advice_bytes = advice_path.read_bytes()
        observed = hashlib.sha256(advice_bytes).hexdigest()
        if observed != declaration.advice.sha256:
            raise ValueError(
                "advice artifact identity mismatch: "
                f"declared {declaration.advice.sha256}, observed {observed}"
            )
        try:
            advice_content = json.loads(advice_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"advice artifact is not valid {declaration.advice.content_type}: {exc}"
            ) from exc
        if not isinstance(advice_content, dict) or not advice_content:
            raise ValueError("advice artifact must be a non-empty JSON object")

    module_states = {
        module: adapters[adapter]
        for module, adapters in declaration.modules.items()
        if adapter in adapters
    }
    for module in required_modules:
        if module not in module_states:
            raise ValueError(
                f"information treatment does not declare module {module!r} for adapter {adapter!r}"
            )

    return ResolvedInformationTreatment(
        declaration=declaration,
        manifest_path=manifest,
        manifest_sha256=_sha256(manifest),
        repository_root=root,
        task_package_path=task_package,
        advice_path=advice_path,
        adapter=adapter,
        module_states=module_states,
    )


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("siderius-args", "receipt"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--require-module", action="append", default=[])
    args = parser.parse_args()
    resolved = resolve_information_treatment(
        args.manifest,
        repository_root=args.repository_root,
        adapter=args.adapter,
        required_modules=tuple(args.require_module),
    )
    if args.command == "receipt":
        print(json.dumps(resolved.receipt(), sort_keys=True))
    else:
        print("\n".join(resolved.siderius_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
