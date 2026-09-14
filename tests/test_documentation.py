"""Small, repository-local guards for the human README navigation."""

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _relative_links(path: Path):
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        target = target.split("#", 1)[0]
        if target and not target.startswith(("http:", "https:", "mailto:")):
            yield target


def test_human_indexes_link_to_existing_entrypoints():
    for relative in ("README.md", "tasks/README.md", "experiments/README.md", "campaigns/README.md"):
        page = ROOT / relative
        for target in _relative_links(page):
            assert (page.parent / target).exists(), f"broken link in {relative}: {target}"


def test_current_indexes_keep_task_and_campaign_boundaries_visible():
    root = (ROOT / "README.md").read_text()
    gold = (ROOT / "campaigns/tidmad_gold/docs/CURRENT.md").read_text()
    assert "tasks/" in root and "experiments/" in root and "campaigns/" in root
    assert "stopped" in gold.lower()
    assert "not authorized" in gold.lower()
    assert "official_campaign_golden_notebook.md" in gold


def test_tidmad_legacy_paths_are_explicitly_historical():
    for relative in ("tasks/tidmad/STATUS.md", "tasks/tidmad/PROVENANCE.md"):
        text = (ROOT / relative).read_text()
        if "examples/tidmad/" in text:
            assert "historical" in text.lower()

