"""Create independent low-cost tutorial routing without editing scientific assets."""

from pathlib import Path

from workflows.llm_config import WorkflowLLMConfig

TEST_LLM_CONFIG = Path(__file__).with_name("openai_smoke_luna.json")


def write_test_llm_config(destination: Path) -> None:
    """Validate the template and save it once in a new external project."""
    content = TEST_LLM_CONFIG.read_text()
    WorkflowLLMConfig.model_validate_json(content)
    with destination.open("x") as stream:
        stream.write(content)
