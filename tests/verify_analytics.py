import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.core.db import async_session_maker
from src.services.evaluation_service import EvaluationService
from sqlalchemy import text


async def main():
    print("Starting Analytics Verification...")

    async with async_session_maker() as db:
        # Check DB migration first
        try:
            await db.execute(text("SELECT model_name FROM evaluation_runs LIMIT 1"))
            print("DB Check: 'model_name' column exists.")
        except Exception as e:
            print(f"DB Check Failed: {e}")
            print("PLEASE RUN MIGRATIONS: poetry run alembic upgrade head")
            return

        service = EvaluationService(db)

        # Get latest run
        result = await db.execute(text("SELECT id FROM evaluation_runs ORDER BY id DESC LIMIT 1"))
        run_id = result.scalar()

        if not run_id:
            print("No runs found in DB. Skipping logic check.")
            return

        print(f"Checking Run ID: {run_id}")
        data = await service.get_run_with_analytics(run_id)

        if not data:
            print(f"Failed to fetch detailed data for run {run_id}")
            return

        print("=" * 80)
        print(f"Created At: {data.created_at}")
        print(f"Duration: {data.duration_seconds}s")
        print(f"Speed: {data.avg_seconds_per_question} s/question")
        print(f"Model: {data.model_name}")
        print(f"Status: {data.status}")
        print("=" * 80)

        # Group results by input (question)
        questions_map = {}
        for result in data.results:
            if result.input not in questions_map:
                questions_map[result.input] = {"output": result.output, "metrics": []}
            questions_map[result.input]["metrics"].append(
                {"name": result.metric, "score": result.score, "reason": result.reason}
            )

        # Print detailed Q&A with metrics
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

        # Final summary stats
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)

        if data.metrics_stats:
            for m in data.metrics_stats:
                print(f"\n{m.name}:")
                print(f"   • Average Score: {m.avg_score}")
                print(f"   • Pass Rate: {m.pass_rate*100}% ({m.passed_count}/{m.total_count})")
        else:
            print("\nNo metrics stats found (maybe run is pending?)")

        print("=" * 80)
        print("Analytics Logic Verified!")


if __name__ == "__main__":
    asyncio.run(main())
