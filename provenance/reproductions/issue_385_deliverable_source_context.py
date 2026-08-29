"""External acceptance witness for SIDERIUS issue #385."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, ClassVar

import torch


def main() -> None:
    from execute_tools.generic_inference import run_generic_inference
    from execute_tools.task_data_path import (
        DeliverableWriteRequest,
        EpochSamplingParams,
        EvalMaterializationParams,
        EvaluationReadRequest,
    )

    class SourceAwareTask:
        task_data_path_id: ClassVar[str] = "external_source_aware_witness"

        @staticmethod
        def _dataset(
            scope: object, data_dir: str
        ) -> list[tuple[torch.Tensor, torch.Tensor]]:
            source = Path(data_dir) / "values.txt"
            values = [
                float(value)
                for value in source.read_text(encoding="utf-8").splitlines()
            ]
            indices = tuple(int(index) for index in scope)  # type: ignore[arg-type]
            return [
                (torch.tensor([values[index]]), torch.tensor(values[index] + 100.0))
                for index in indices
            ]

        def training_dataset(self, scope: object, params: EpochSamplingParams) -> Any:
            return self._dataset(scope, params.data_dir)

        def validation_dataset(
            self, scope: object, params: EvalMaterializationParams
        ) -> Any:
            return self._dataset(scope, params.data_dir)

        def write_deliverable(
            self, outputs: Any, request: DeliverableWriteRequest
        ) -> None:
            context = getattr(request, "source_context", None)
            if context is None:
                raise RuntimeError(
                    "generic inference did not carry the run-bound deliverable source context"
                )
            dataset = self.validation_dataset(
                request.task_scope,
                EvalMaterializationParams(data_dir=context.data_dir),
            )
            predictions = list(outputs)
            if (
                len(dataset) != context.sample_count
                or len(predictions) != context.sample_count
            ):
                raise RuntimeError("deliverable source and prediction counts differ")
            rows = [
                f"{float(prediction.item())},{float(target.item())}"
                for prediction, (_model_input, target) in zip(
                    predictions, dataset, strict=True
                )
            ]
            (Path(request.output_dir) / "prediction_and_target.csv").write_text(
                "prediction,target\n" + "\n".join(rows) + "\n",
                encoding="utf-8",
            )

        def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
            return (
                Path(request.deliverable_dir) / "prediction_and_target.csv"
            ).read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="siderius-issue-385-") as root:
        root_path = Path(root)
        data_dir = root_path / "data"
        output_dir = root_path / "output"
        data_dir.mkdir()
        output_dir.mkdir()
        (data_dir / "values.txt").write_text("1\n2\n3\n", encoding="utf-8")
        task = SourceAwareTask()
        run_generic_inference(
            data_path=task,
            task_scope=(2, 0),
            model=torch.nn.Identity(),
            device=torch.device("cpu"),
            data_dir=str(data_dir),
            batch_size=2,
            write_request=DeliverableWriteRequest(
                output_dir=str(output_dir),
                exp_id="issue385",
                run_name="external_witness",
                model_type="identity",
            ),
        )
        payload = task.read_evaluation_payload(
            EvaluationReadRequest(
                deliverable_dir=str(output_dir),
                exp_id="issue385",
                run_name="external_witness",
                model_type="identity",
            )
        )
        expected = "prediction,target\n3.0,103.0\n1.0,101.0\n"
        if payload != expected:
            raise RuntimeError(f"prediction/source alignment changed: {payload!r}")

    print("PASS: deliverable writing recovered prediction-aligned task values")


if __name__ == "__main__":
    main()
