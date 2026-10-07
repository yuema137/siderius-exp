"""Historical presentation selected explicitly by experiment configuration."""

import json
from functools import wraps
from pathlib import Path

from agent.prompt_rendering import PromptRenderingProfile, rendering_assembly_digest

_ROOT = Path(__file__).parent
_INTERPRETATION = frozenset({"interpretation.model_system", "interpretation.model_user"})


def _template(filename: str) -> str:
    if Path(filename).name != filename or not filename.endswith(".md"):
        raise ValueError("Historical proposal template must be a declared Markdown basename")
    return (_ROOT / "templates" / filename).read_text()


def _without_appendix() -> str:
    return ""


def _analysis_view(renderer):
    @wraps(renderer)
    def render(**kwargs):
        # Recovery is an execution declaration introduced after this source.
        # The renderer receives its own copy, and cannot mutate saved inputs.
        if "analysis_input" in kwargs:
            value = kwargs["analysis_input"]
            kwargs["analysis_input"] = value.model_copy(update={"recovery_policy": None})
        return renderer(**kwargs)

    return render


def _profile(
    name: str,
    *,
    early_contract: bool,
    old_interpretation: bool = False,
    with_analysis: bool = False,
) -> PromptRenderingProfile:
    qualification = json.loads((_ROOT / "qualification.json").read_text())
    qualified = {qualification["assembly_sha256"]}
    qualified.update(row["assembly_sha256"] for row in qualification.get("additional_assemblies", []))
    if rendering_assembly_digest() not in qualified:
        raise ValueError(
            "This historical profile has not been qualified for the installed infra "
            "renderers. Use the documented infra revision or rerun offline qualification."
        )
    renderers = {"proposal.template": _template}
    native = set(_INTERPRETATION)
    if early_contract:
        renderers["native_training.appendix"] = _without_appendix
    else:
        native.add("native_training.appendix")
    if old_interpretation:
        from . import interpretation_345c802d as old

        renderers["interpretation.model_system"] = old._build_per_model_system_prompt
        renderers["interpretation.model_user"] = old._build_per_model_prompt
        native -= _INTERPRETATION
    if with_analysis:
        from . import analysis_c0467447 as old_analysis

        for stage in (
            "skill_selection",
            "analysis_plan",
            "generated_program",
            "report_synthesis",
            "generated_skill_promotion",
        ):
            renderers[f"data_analysis.{stage}"] = _analysis_view(
                getattr(old_analysis, f"render_{stage}_prompt")
            )

        def repair(*, stage, **kwargs):
            # The old renderer predates a stage-specific instruction block.
            return old_analysis.render_structured_output_repair_prompt(**kwargs)

        renderers["data_analysis.structured_output_repair"] = repair
    sources = {
        str(p.relative_to(_ROOT)): p
        for p in _ROOT.rglob("*")
        if p.is_file() and p.suffix in {".py", ".md", ".json"}
    }
    return PromptRenderingProfile(name, "1", renderers, frozenset(native), sources)


def early() -> PromptRenderingProfile:
    return _profile("paper-early-v1", early_contract=True)


def late() -> PromptRenderingProfile:
    return _profile("paper-late-v1", early_contract=False)


def tidmad_noprior() -> PromptRenderingProfile:
    return _profile("paper-tidmad-noprior-v1", early_contract=True, old_interpretation=True)


def analysis() -> PromptRenderingProfile:
    return _profile("paper-analysis-c0467447-v1", early_contract=False, with_analysis=True)
