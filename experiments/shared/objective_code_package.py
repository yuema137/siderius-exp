"""Finite loss source transport using the framework's captured package loader."""

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from agent.schemas.data_analysis.common import canonical_sha256
from core.local_code import CodePackageDeclaration, bind_code_package, capture_package
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ObjectiveCodePackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entrypoint: str
    sources: dict[str, str] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def finite_members(self):
        CodePackageDeclaration(root=".", files=tuple(self.sources))
        if self.entrypoint not in self.sources:
            raise ValueError("loss entrypoint is absent from captured package")
        if sum(len(value.encode()) for value in self.sources.values()) > 1048576:
            raise ValueError("loss package exceeds source transport limit")
        return self

    @property
    def sha256(self) -> str:
        return canonical_sha256(self)


def require_package_source(source: str, package: ObjectiveCodePackage | None) -> None:
    if package is not None and package.sources[package.entrypoint] != source:
        raise ValueError("loss source differs from captured package entrypoint")


@contextmanager
def bound_objective_source(
    source: str, package: ObjectiveCodePackage | None
) -> Iterator[Path]:
    """Stage exact bytes, bind native imports; execute only inside confinement."""
    require_package_source(source, package)
    with tempfile.TemporaryDirectory(prefix="objective-source-") as directory:
        root = Path(directory)
        if package is None:
            path = root / "loss.py"
            path.write_text(source)
            yield path
            return
        for name, content in package.sources.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        captured = capture_package(
            CodePackageDeclaration(root=".", files=tuple(package.sources)), root
        )
        with bind_code_package(captured):
            yield root / package.entrypoint
