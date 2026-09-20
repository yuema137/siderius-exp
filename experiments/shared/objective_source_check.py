"""Non-executing checks for obvious custom-objective side effects.

AST inspection is only one review stage, never a Python security sandbox.
Permitted imports must be frozen by deployment, not selected by the agent.
"""

import ast
from pathlib import PurePosixPath

from agent.schemas.data_analysis.common import Sha256
from pydantic import BaseModel, ConfigDict

from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial

_DYNAMIC = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
}
_IO = {
    "open",
    "print",
    "input",
    "load",
    "save",
    "read_text",
    "read_bytes",
    "write_text",
    "write_bytes",
    "tofile",
    "fromfile",
    "loadtxt",
    "savetxt",
    "memmap",
    "system",
    "popen",
    "connect",
    "urlopen",
}


class SourceFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    file: str
    line: int
    reason: str


class ObjectiveSourceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    material_sha256: Sha256
    findings: tuple[SourceFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings


def inspect_objective_source(
    material: ObjectiveReviewMaterial, *, allowed_import_roots: frozenset[str]
) -> ObjectiveSourceCheck:
    """Parse every source file without imports or other execution.

    Covers direct/aliased imports and references to known effectful operations.
    Other Python constructions still require semantic review and OS isolation.
    A clean result is not permission to execute beside private targets.
    """
    material = ObjectiveReviewMaterial.model_validate(material).model_copy(deep=True)
    findings = []
    for name, source in material.sources.items():
        try:
            tree = ast.parse(source, filename=name)
        except (SyntaxError, ValueError) as exc:
            findings.append(
                SourceFinding(
                    file=name,
                    line=getattr(exc, "lineno", 0) or 0,
                    reason="Source could not be parsed",
                )
            )
            continue
        for node in ast.walk(tree):
            reasons = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in allowed_import_roots:
                        reasons.append(
                            f"Import requires approved dependency: {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if not _declared_relative_import(name, node, material.sources):
                        reasons.append(
                            "Relative import is absent from reviewed source files"
                        )
                elif (node.module or "").split(".")[0] not in allowed_import_roots:
                    reasons.append("Unapproved dependency import")
                if any(alias.name == "*" for alias in node.names):
                    reasons.append("Wildcard import obscures reviewed dependencies")
                for alias in node.names:
                    if alias.name in _IO | _DYNAMIC:
                        reasons.append(
                            f"Effectful/dynamic imported operation: {alias.name}"
                        )
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in _IO | _DYNAMIC:
                    reasons.append(f"Effectful/dynamic operation: {node.id}")
            elif isinstance(node, ast.Attribute) and (
                node.attr in _IO | _DYNAMIC
                or (node.attr.startswith("__") and node.attr != "__init__")
            ):
                reasons.append(f"Effectful/dynamic attribute: {node.attr}")
            for reason in reasons:
                findings.append(
                    SourceFinding(file=name, line=node.lineno, reason=reason)
                )
    return ObjectiveSourceCheck(
        material_sha256=material.sha256, findings=tuple(findings)
    )


def _declared_relative_import(
    file: str, node: ast.ImportFrom, sources: dict[str, str]
) -> bool:
    """Resolve only finite relative names; the native importer enforces loading."""
    parent = list(PurePosixPath(file).parts[:-1])
    if node.level > len(parent) + 1:
        return False
    if node.level > 1:
        parent = parent[: -(node.level - 1)]
    parts = [*parent, *((node.module or "").split(".") if node.module else [])]
    base = "/".join(parts)
    if base and (base + ".py" in sources or base + "/__init__.py" in sources):
        return True
    # A namespace package has only explicitly supplied children. For `from .
    # import helper`, require each named child, not a blanket relative allowance.
    prefix = base + "/" if base else ""
    return all(
        prefix + alias.name + ".py" in sources
        or prefix + alias.name + "/__init__.py" in sources
        for alias in node.names
    )
