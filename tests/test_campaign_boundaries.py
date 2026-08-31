from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGNS = (
    "tidmad_gold",
    "oxford_iiit_pet",
    "davis_future_prediction",
    "cancer_gene_identification",
)
PLANNED_CAMPAIGNS = CAMPAIGNS[1:]


def test_all_scientific_tasks_have_campaign_packages() -> None:
    for campaign in CAMPAIGNS:
        assert (ROOT / "campaigns" / campaign / "README.md").is_file()


def test_planned_campaigns_are_explicitly_non_launchable() -> None:
    for campaign in PLANNED_CAMPAIGNS:
        package = ROOT / "campaigns" / campaign
        readme = (package / "README.md").read_text(encoding="utf-8")
        assert "Status: planned; not launchable" in readme
        assert "Launch authorization: not authorized" in readme
        assert "Workflow selection: TBD" in readme
        assert not any(package.glob("*.sh"))
        assert not any(package.glob("*.py"))


def test_deployment_intent_stays_out_of_task_packages() -> None:
    for task_readme in (ROOT / "tasks").glob("*/README.md"):
        text = task_readme.read_text(encoding="utf-8")
        assert "campaign pool" not in text.lower()
