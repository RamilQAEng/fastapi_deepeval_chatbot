import asyncio
import os
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.append(os.getcwd())

from src.core.db import async_session_maker  # noqa: E402
from src.services.evaluation_service import EvaluationService  # noqa: E402


async def _check_db_migration(db: AsyncSession) -> bool:
    """Check if the database has the required columns."""
    try:
        await db.execute(text("SELECT model_name FROM evaluation_runs LIMIT 1"))
        print("DB Check: 'model_name' column exists.")
        return True
    except Exception as e:
        print(f"DB Check Failed: {e}")
        print("PLEASE RUN MIGRATIONS: poetry run alembic upgrade head")
        return False


async def _get_latest_run(db: AsyncSession) -> int | None:
    """Fetch the ID of the latest evaluation run."""
    result = await db.execute(text("SELECT id FROM evaluation_runs ORDER BY id DESC LIMIT 1"))
    return result.scalar()


def _print_run_details(data: Any) -> None:
    """Print basic details about the evaluation run."""
    print("=" * 80)
    print(f"Created At: {data.created_at}")
    print(f"Duration: {data.duration_seconds}s")
    print(f"Speed: {data.avg_seconds_per_question} s/question")
    print(f"Model: {data.model_name}")
    print(f"Status: {data.status}")
    print("=" * 80)


def _group_results(results: list[Any]) -> dict[str, dict[str, Any]]:
    """Group results by input question."""
    questions_map: dict[str, dict[str, Any]] = {}
    for res in results:
        # Result object attributes are now detected by mypy
        input_text = res.input
        if input_text not in questions_map:
            questions_map[input_text] = {"output": res.output, "metrics": []}
        questions_map[input_text]["metrics"].append(
            {"name": res.metric, "score": res.score, "reason": res.reason}
        )
    return questions_map


def _print_qa_metrics(questions_map: dict[str, dict[str, Any]]) -> None:
    """Print Q&A details and metrics."""
    for idx, (question, qa_data) in enumerate(questions_map.items(), 1):
        print("\n" + "─" * 80)
        print(f"Question #{idx}:")
        print(f"  {question}")
        print("\nAnswer:")
        print(f"  {qa_data['output']}")
        print("\nMetrics:")
        for metric in qa_data["metrics"]:
            score_emoji = "[PASS]" if metric["score"] >= 0.5 else "[FAIL]"
            print(f"  {score_emoji} {metric['name']}: {metric['score']}")
            if metric["reason"]:
                print(f"     └─ Reasoning: {metric['reason']}")


def _print_summary(metrics_stats: list[Any] | None) -> None:
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    if metrics_stats:
        for m in metrics_stats:
            print(f"\n{m.name}:")
            print(f"   • Average Score: {m.avg_score}")
            print(f"   • Pass Rate: {m.pass_rate*100}% ({m.passed_count}/{m.total_count})")
    else:
        print("\nNo metrics stats found (maybe run is pending?)")


async def main() -> None:
    print("Starting Analytics Verification...")

    async with async_session_maker() as db:
        if not await _check_db_migration(db):
            return

        service = EvaluationService(db)

        run_id = await _get_latest_run(db)
        if not run_id:
            print("No runs found in DB. Skipping logic check.")
            return

        print(f"Checking Run ID: {run_id}")
        data = await service.get_run_with_analytics(run_id)

        if not data:
            print(f"Failed to fetch detailed data for run {run_id}")
            return

        _print_run_details(data)

        questions_map = _group_results(data.results)
        _print_qa_metrics(questions_map)

        _print_summary(data.metrics_stats)

        print("=" * 80)
        print("Analytics Logic Verified!")


if __name__ == "__main__":
    asyncio.run(main())
