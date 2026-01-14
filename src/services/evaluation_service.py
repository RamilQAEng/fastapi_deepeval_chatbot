from typing import Any

from deepeval import evaluate as deepeval_evaluate
from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric, FaithfulnessMetric
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.evaluation import Dataset, EvaluationResult, EvaluationRun, RunStatus


class EvaluationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_run(self, dataset_id: int, metrics: list[str]) -> EvaluationRun:
        run = EvaluationRun(dataset_id=dataset_id, metrics_used=metrics, status=RunStatus.PENDING)
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def run_evaluation(self, run_id: int) -> None:
        run = await self.db.get(EvaluationRun, run_id)
        if not run:
            return

        # Load dataset
        # We need to lazy load or join. Ideally query it.
        stmt = select(Dataset).where(Dataset.id == run.dataset_id)
        result = await self.db.execute(stmt)
        dataset = result.scalar_one()

        test_cases = []
        for item in dataset.content:
            # Assuming item matches RAGTestCase structure from JSON
            tc = LLMTestCase(
                input=item["input"],
                actual_output=item["actual_output"],
                retrieval_context=item["retrieval_context"],
                expected_output=item.get("expected_output"),
                context=item.get("context"),
            )
            test_cases.append(tc)

        from deepeval.models import GPTModel

        from src.core.config import settings

        # Configure model for evaluation (OpenRouter)
        # GPTModel accepts base_url and api_key directly
        eval_model = GPTModel(
            model=settings.DEEPEVAL_OPENAI_MODEL,
            base_url=settings.OPENAI_API_BASE,
            api_key=settings.OPENAI_API_KEY,
        )

        # Map metrics with custom model
        metric_objects: list[BaseMetric] = []
        if "answer_relevancy" in run.metrics_used:
            metric_objects.append(AnswerRelevancyMetric(threshold=0.5, model=eval_model))
        if "faithfulness" in run.metrics_used:
            metric_objects.append(FaithfulnessMetric(threshold=0.5, model=eval_model))
        if "contextual_precision" in run.metrics_used:
            metric_objects.append(ContextualPrecisionMetric(threshold=0.5, model=eval_model))

        try:
            # Run DeepEval
            evaluation_result: Any = deepeval_evaluate(test_cases, metric_objects)  # type: ignore[operator]

            # Save results
            for res in evaluation_result.test_results:
                # res is TestResult
                for metric_res in res.metrics_data:
                    eval_result = EvaluationResult(
                        run_id=run.id,
                        input=res.input,
                        output=res.actual_output,
                        score=metric_res.score,
                        reason=metric_res.reason,
                        metric_name=metric_res.name,
                    )
                    self.db.add(eval_result)

            run.status = RunStatus.COMPLETED
        except Exception as e:
            run.status = RunStatus.FAILED
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Evaluation Run {run.id} Failed", exc_info=True)

            # Keep detailed traceback as fallback/debug artifact
            import traceback

            with open("evaluation_errors.log", "a") as f:
                f.write(f"Run {run.id} Failed: {e}\n")
                f.write(traceback.format_exc())
                f.write("-" * 50 + "\n")

        from datetime import datetime
        from zoneinfo import ZoneInfo

        run.finished_at = datetime.now(ZoneInfo("UTC"))
        await self.db.commit()
