from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_db
from src.schemas.models import DatasetConfig, EvaluationRequest, GenerateDatasetRequest, RAGTestCase
from src.services.dataset_service import DatasetService
from src.services.evaluation_service import EvaluationService

rag_router = APIRouter(prefix="/api/v1", tags=["RAG"])


@rag_router.post("/datasets/generate")
async def generate_dataset(
    request: GenerateDatasetRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    if not request.text and not request.file_path:
        raise HTTPException(status_code=400, detail="Either text or file_path must be provided")

    service = DatasetService(db)
    # Background generation could be better, but for MVP we wait.
    # Note: text context might be large.

    text_content = request.text or ""
    if request.file_path:
        raise HTTPException(status_code=501, detail="File upload not yet supported")

    test_cases = await service.generate_synthetic_from_text(text_content, request.num_questions)

    # Auto-save as a new dataset
    dataset = await service.create_dataset(
        name=f"Generated from {text_content[:20]}...", test_cases=test_cases
    )

    return {"dataset_id": dataset.id, "count": len(test_cases), "status": "created"}


@rag_router.post("/datasets/upload")
async def upload_dataset(
    config: DatasetConfig,
    run_eval: bool = False,
    background_tasks: BackgroundTasks | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    service = DatasetService(db)

    dataset = await service.create_dataset(
        name=f"Uploaded Dataset {len(config.test_cases)} items", test_cases=config.test_cases
    )

    response: dict[str, Any] = {
        "dataset_id": dataset.id,
        "count": len(config.test_cases),
        "status": "created",
    }

    if run_eval:
        eval_service = EvaluationService(db)
        # Default metrics for now
        metrics = ["faithfulness", "answer_relevancy"]
        run = await eval_service.create_run(dataset.id, metrics)

        # We need background_tasks here
        if background_tasks:
            background_tasks.add_task(eval_service.run_evaluation, run.id)
            response["eval_run_id"] = run.id
            response["eval_status"] = "pending"

    return response


@rag_router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    service = DatasetService(db)
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {
        "id": dataset.id,
        "name": dataset.name,
        "created_at": dataset.created_at.strftime("%d %m %Y") if dataset.created_at else None,
        "content": dataset.content,
    }


@rag_router.post("/evaluations/run")
async def run_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    service = EvaluationService(db)
    run = await service.create_run(request.dataset_id, request.metrics)

    # Run in background
    background_tasks.add_task(service.run_evaluation, run.id)

    return {"run_id": run.id, "status": "pending"}


@rag_router.get("/evaluations/{run_id}")
async def get_evaluation_status(run_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    # Simple polling endpoint
    # We need to implement get_run in service or query here
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.models.evaluation import EvaluationRun

    stmt = (
        select(EvaluationRun)
        .options(selectinload(EvaluationRun.results))
        .where(EvaluationRun.id == run_id)
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    results_data = [
        {
            "metric": res.metric_name,
            "score": res.score,
            "reason": res.reason,
            "input": res.input[:50] + "..." if res.input else None,
        }
        for res in run.results
    ]

    return {
        "id": run.id,
        "status": run.status,
        "metrics": run.metrics_used,
        "created_at": run.created_at.strftime("%d %m %Y") if run.created_at else None,
        "results": results_data,
    }


@rag_router.get("/template")
async def get_dataset_template() -> dict[str, Any]:
    """Returns a sample JSON structure for uploading datasets."""
    sample = DatasetConfig(
        name="Sample Dataset",
        test_cases=[
            RAGTestCase(
                input="Sample Question",
                actual_output="Sample Answer",
                retrieval_context=["Context chunk 1", "Context chunk 2"],
                expected_output="Golden Answer",
                context=["Golden context"],
            )
        ],
    )
    return sample.model_dump()
