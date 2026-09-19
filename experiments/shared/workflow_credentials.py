"""Name-only credential requirements derived from enabled workflow roles."""

from pathlib import Path

from workflows.llm_config import WorkflowLLMConfig


def required_workflow_api_keys(
    config: Path, *, disabled_roles: frozenset[str] = frozenset()
) -> set[str]:
    """Read enabled provider names without displaying credentials."""

    provider_keys = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    payload = WorkflowLLMConfig.from_json(str(config)).model_dump(exclude_none=True)
    unknown_roles = disabled_roles - WorkflowLLMConfig.model_fields.keys()
    if unknown_roles:
        raise ValueError(f"unknown disabled workflow roles: {sorted(unknown_roles)}")
    for role in disabled_roles:
        payload.pop(role, None)
    providers: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            provider = value.get("provider")
            if isinstance(provider, str):
                providers.add(provider)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    if not providers:
        raise ValueError("Workflow LLM config declares no enabled provider")
    unknown = providers - provider_keys.keys()
    if unknown:
        raise ValueError(
            f"unsupported LLM provider in launch config: {sorted(unknown)}"
        )
    return {provider_keys[provider] for provider in providers}
