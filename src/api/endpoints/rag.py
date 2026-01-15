from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_db
from src.schemas.models import (
    DatasetConfig,
    EvaluationRequest,
    EvaluationResponse,
    GenerateDatasetRequest,
    RAGTestCase,
)
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
    background_tasks: BackgroundTasks,
    run_eval: bool = False,
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


@rag_router.get("/evaluations/{run_id}", response_model=EvaluationResponse)
async def get_evaluation_status(run_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    service = EvaluationService(db)
    response = await service.get_run_with_analytics(run_id)
    if not response:
        raise HTTPException(status_code=404, detail="Run not found")

    # Truncate long strings for API response to keep payload small
    for res in response.results:
        # Pydantic models are not dicts, modify attributes directly
        if res.input and len(res.input) > 200:
            res.input = res.input[:200] + "..."
        if res.output and len(res.output) > 200:
            res.output = res.output[:200] + "..."

    return response


@rag_router.get("/evaluations/{run_id}/download")
async def download_evaluation_report(
    run_id: int, format: Literal["csv", "xlsx"] = "xlsx", db: AsyncSession = Depends(get_db)
) -> Response:
    service = EvaluationService(db)
    data = await service.get_run_with_analytics(run_id)

    if not data:
        raise HTTPException(status_code=404, detail="Run not found")

    from io import BytesIO

    import pandas as pd

    # Flatten results for DataFrame
    rows = []
    for res in data.results:
        rows.append(
            {
                "Input": res.input,
                "Output": res.output,
                "Metric": res.metric,
                "Score": res.score,
                "Reason": res.reason,
            }
        )

    df = pd.DataFrame(rows)

    # Create filename
    # Sanitize created_at for filename
    date_str = data.created_at.replace(" ", "_").replace(":", "-").replace(".", "-")
    filename = f"report_run_{run_id}_{date_str}"

    if format == "csv":
        # Simple CSV
        stream = BytesIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )

    elif format == "xlsx":
        stream = BytesIO()
        # Ensure openpyxl is installed (we added it)
        with pd.ExcelWriter(stream, engine="openpyxl") as writer:
            # Sheet 1: Summary
            summary_data = {
                "Run ID": [data.id],
                "Model": [data.model_name],
                "Date": [data.created_at],
                "Duration (s)": [data.duration_seconds],
                "Avg Speed (s/q)": [data.avg_seconds_per_question],
                "Status": [data.status],
            }
            # Add metric stats to summary
            for m in data.metrics_stats:
                summary_data[f"{m.name} Avg"] = [m.avg_score]
                summary_data[f"{m.name} Pass Rate"] = [m.pass_rate]

            pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)

            # Sheet 2: Detailed Results
            df.to_excel(writer, sheet_name="Details", index=False)

        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )

    raise HTTPException(status_code=400, detail="Invalid format")


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
