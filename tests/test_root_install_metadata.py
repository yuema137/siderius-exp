"""Catch #279: local compatibility releases leaving frozen root metadata stale."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_root_local_packages_match_shipped_metadata() -> None:
    """A stale root pin, lock identity, source or optional pin fails comparison.

    uv frozen sync alone accepts stale local metadata. Compare the declarations
    directly so the root installation follows releases of its local packages.
    These packages use exact optional pins; this is not a dependency resolver.
    """
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    packages = {package["name"]: package for package in lock["package"]}
    root_requires = packages["siderius-exp"]["metadata"]["requires-dist"]

    local_sources = {
        name: source
        for name, source in project["tool"]["uv"]["sources"].items()
        if "path" in source
    }
    assert local_sources, "root installation must retain its local package sources"
    for name, source in local_sources.items():
        local = tomllib.loads((ROOT / source["path"] / "pyproject.toml").read_text())[
            "project"
        ]
        assert source.get("editable") is False, name
        assert local["name"] == name
        assert f"{name}=={local['version']}" in project["project"]["dependencies"]
        locked = packages[name]
        assert locked["version"] == local["version"], name
        assert locked["source"] == {"directory": source["path"]}, name
        assert {"name": name, "directory": source["path"]} in root_requires

        optional = local.get("optional-dependencies", {})
        metadata = locked.get("metadata", {})
        assert sorted(metadata.get("provides-extras", [])) == sorted(optional)
        expected = []
        for extra, requirements in optional.items():
            for requirement in requirements:
                dependency, separator, version = requirement.partition("==")
                assert separator and version, requirement
                expected.append((dependency, f"extra == '{extra}'", f"=={version}"))
        observed = [
            (
                requirement["name"],
                requirement.get("marker"),
                requirement.get("specifier"),
            )
            for requirement in metadata.get("requires-dist", [])
        ]
        assert sorted(observed) == sorted(expected), name
