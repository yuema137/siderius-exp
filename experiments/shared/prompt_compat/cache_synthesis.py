"""Capture the actual interpreter's cached-only synthesis path without providers."""

from __future__ import annotations

from tempfile import TemporaryDirectory


def render_cached_synthesis(arguments: dict) -> tuple[str, str]:
    """Replay saved cache text/stats with explicitly reconstructed input context.

    The supplied input is not claimed to be the historical request envelope.
    Only the temporary workspace spelling is normalized in captured prompts.
    """
    from agent.schemas.interpretation import InterpretationInput
    from nodes.result_interpretation_agent import ResultInterpretationAgent

    messages = []

    class CaptureBridge:
        def __init__(self, **kwargs):
            pass

        def emit_marker(self, **kwargs):
            pass

        def generate(self, system_prompt, user_prompt, **kwargs):
            if kwargs.get("label") != "interpretation.synthesis":
                raise AssertionError(
                    f"Unexpected request during cache replay: {kwargs.get('label')}"
                )
            messages.append((system_prompt, user_prompt))
            return {
                "key_findings": [],
                "bottlenecks": [],
                "take_home_message": "Offline capture",
            }

    with TemporaryDirectory(prefix="siderius-cache-replay-") as workspace:
        supplied = dict(arguments["input"])
        if supplied.get("summaries"):
            raise ValueError(
                "Cache-only replay does not accept newly generated model summaries"
            )
        supplied["storage"] = {
            "backend": "local",
            "local": {"workspace": workspace, "run_name": "offline"},
        }
        inp = InterpretationInput.model_validate(supplied)
        agent = ResultInterpretationAgent(bridge_factory=CaptureBridge)
        output = agent.run(inp)
        if set(output.scientific_aggregation["included"]) != set(
            arguments["expected_included"]
        ):
            raise ValueError(
                "Recovered scientific membership differs from the archived evidence"
            )
        expected = int(len(inp.model_knowledge_cache) > 1)
        if output.is_degraded or len(messages) != expected:
            raise ValueError(
                "Cache replay did not reach the expected non-degraded synthesis path"
            )
        if not messages:
            return "", ""  # The ordinary single-model path makes no synthesis request.
        system, user = messages[0]
        return system.replace(workspace, "<OFFLINE_WORKSPACE>"), user.replace(
            workspace, "<OFFLINE_WORKSPACE>"
        )
