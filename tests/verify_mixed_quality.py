"""
Test script to verify evaluation metrics with mixed quality answers.
Generates a dataset with 10 questions and varying answer quality (Russian):
- 3 excellent answers (score 0.9-1.0)
- 3 medium answers (score 0.5-0.7)
- 4 poor answers (score 0.0-0.3)
"""

import asyncio
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

# Constants
BASE_URL = "http://127.0.0.1:8000/api/v1"
MSK_TZ = ZoneInfo("Europe/Moscow")


def get_msk_time() -> str:
    return datetime.now(MSK_TZ).isoformat()


# Common retrieval context strings
PRICE_OBJECTION_CONTEXT = (
    "Если клиент утверждает, что нашел более дешевое предложение на Лада Веста Sport в другом месте, "
    "не предлагайте скидку сразу. Сначала подчеркните, что в нашу цену включена гарантия 'Полная Защита' "
    "стоимостью 150,000 рублей."
)

CANCELLATION_CONTEXT = (
    "Клиенты, звонящие с отменой в течение 24 часов, часто испытывают сомнения после покупки. "
    "Менеджер должен назначить видеозвонок для повторной демонстрации функций автомобиля. "
    "Не обрабатывайте отмену по телефону/email без устного подтверждения от специалиста по удержанию."
)

# Test data with mixed quality answers (Russian)
# Full dataset: 3 excellent + 3 medium + 4 poor = 10 questions
MIXED_QUALITY_DATASET = {
    "questions": [
        # === ОТЛИЧНЫЕ ОТВЕТЫ (3) ===
        {
            "question": "Какая гарантия предоставляется на Лада Веста Sport?",
            "answer": "На Лада Веста Sport предоставляется расширенная гарантия 'Полная Защита' стоимостью 150,000 рублей, которая уже включена в цену. Эта гарантия покрывает все основные узлы и агрегаты автомобиля и обеспечивает защиту на 5 лет.",
            "retrieval_context": [PRICE_OBJECTION_CONTEXT],
            "expected_quality": "excellent",
        },
        {
            "question": "Как обрабатывать возражения по цене на Лада Веста Sport?",
            "answer": "При обработке возражений по цене на Лада Веста Sport сначала подчеркните гарантию 'Полная Защита', включенную в цену и оцениваемую в 150,000 рублей. Если клиент все равно настаивает на отказе от покупки, менеджер уполномочен предложить либо скидку 3%, либо бесплатный комплект зимних шин.",
            "retrieval_context": [
                "Если клиент утверждает, что нашел более дешевое предложение на Лада Веста Sport в другом месте, не предлагайте скидку сразу. Сначала подчеркните, что в нашу цену включена гарантия 'Полная Защита' стоимостью 150,000 рублей. Если клиент все равно настаивает на отмене сделки, менеджер может предложить скидку 3% или бесплатный комплект зимних шин."
            ],
            "expected_quality": "excellent",
        },
        {
            "question": "Что должны делать менеджеры, когда клиент хочет отказаться от покупки в течение 24 часов?",
            "answer": "Когда клиенты звонят, чтобы отменить покупку в течение 24 часов из-за сомнений, менеджер должен назначить видеозвонок для повторной демонстрации возможностей автомобиля. Мы не обрабатываем отмену по телефону или email без устного подтверждения от специалиста по удержанию клиентов.",
            "retrieval_context": [CANCELLATION_CONTEXT],
            "expected_quality": "excellent",
        },
        # === СРЕДНИЕ ОТВЕТЫ (3) ===
        {
            "question": "Можем ли мы увеличить стоимость trade-in, если клиент недоволен?",
            "answer": "Да, мы можем увеличить стоимость trade-in до 50,000 рублей в определенных случаях. Это помогает удержать клиентов, рассматривающих другие автосалоны.",
            "retrieval_context": [
                "Если клиент недоволен оценкой trade-in, объясните, что наша оценка включает отмену комиссии за удобство. Мы можем увеличить стоимость trade-in на сумму до 50,000 рублей, если клиент оформит кредит в нашем банке-партнере."
            ],
            "expected_quality": "medium",  # Пропущено условие про кредит
        },
        {
            "question": "Какую скидку могут предложить менеджеры для удержания клиента?",
            "answer": "Менеджеры могут предложить скидку 3% клиентам, желающим отменить покупку. Это часть нашей стратегии удержания.",
            "retrieval_context": [
                "Если клиент все равно настаивает на отмене сделки, менеджер может предложить скидку 3% или бесплатный комплект зимних шин."
            ],
            "expected_quality": "medium",  # Пропущена альтернатива (зимние шины)
        },
        {
            "question": "Как мы обрабатываем запросы на отмену покупки?",
            "answer": "Мы должны постараться понять проблемы клиента и найти с ним решение. Наша команда по удержанию обучена помогать в таких ситуациях.",
            "retrieval_context": [CANCELLATION_CONTEXT],
            "expected_quality": "medium",  # Слишком расплывчато, пропущены конкретные процедуры
        },
        # === ПЛОХИЕ ОТВЕТЫ (4) ===
        {
            "question": "Что включено в гарантию на Лада Веста Sport?",
            "answer": "Лада Веста Sport поставляется со стандартной гарантией 1 год, покрывающей базовые механические неисправности. Расширенная гарантия может быть приобретена отдельно за дополнительную плату.",
            "retrieval_context": [PRICE_OBJECTION_CONTEXT],
            "expected_quality": "poor",  # Противоречит политике (Полная Защита включена)
        },
        {
            "question": "Должны ли мы сразу предлагать скидки, когда клиенты упоминают конкурентов?",
            "answer": "Да, конечно! Мы должны немедленно соответствовать или превосходить цену конкурента, чтобы не потерять продажу. Удовлетворенность клиентов - наш главный приоритет.",
            "retrieval_context": [PRICE_OBJECTION_CONTEXT],
            "expected_quality": "poor",  # Прямо противоречит политике
        },
        {
            "question": "Можем ли мы обработать отмену покупки по email?",
            "answer": "Да, для удобства клиента мы можем обработать отмену по email или телефону. Просто отправьте запрос на отмену в нашу службу поддержки.",
            "retrieval_context": [
                "Не обрабатывайте отмену по телефону/email без устного подтверждения от специалиста по удержанию."
            ],
            "expected_quality": "poor",  # Нарушает требование политики
        },
        {
            "question": "Какова наша комиссия за удобство при trade-in?",
            "answer": "Наш автосалон взимает комиссию за удобство в размере 15,000 рублей за все транзакции trade-in. Эта комиссия покрывает административные расходы на обработку.",
            "retrieval_context": [
                "Если клиент недоволен оценкой trade-in, объясните, что наша оценка включает отмену комиссии за удобство."
            ],
            "expected_quality": "poor",  # Галлюцинация - комиссия отменена, а не взимается
        },
    ]
}


async def create_manual_dataset() -> int | None:
    """Create a dataset manually with mixed quality answers."""
    print(f"\n[{get_msk_time()}] Creating manual dataset with mixed quality answers...")

    # Convert to backend format (DatasetConfig schema)
    test_cases = []
    for item in MIXED_QUALITY_DATASET["questions"]:
        test_cases.append(
            {
                "input": item["question"],
                "actual_output": item["answer"],  # Use actual_output instead of expected_output
                "retrieval_context": item["retrieval_context"],
                "expected_output": item["answer"],  # Optional, but good to have
            }
        )

    payload = {
        "name": f"Mixed Quality Test {datetime.now(MSK_TZ).strftime('%Y-%m-%d %H:%M')}",
        "test_cases": test_cases,  # Use test_cases, not goldens
    }

    print(f"[{get_msk_time()}] Payload (first 2 items):")
    preview = payload.copy()
    preview["test_cases"] = preview["test_cases"][:2]
    print(json.dumps(preview, indent=2, ensure_ascii=False))
    print(f"... and {len(test_cases) - 2} more items")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Use correct endpoint: /datasets/upload
            response = await client.post(f"{BASE_URL}/datasets/upload", json=payload)
            response.raise_for_status()
            data = response.json()

            dataset_id: int | None = data.get("dataset_id")  # Note: response has dataset_id, not id
            print(f"[{get_msk_time()}] Dataset created with ID: {dataset_id}")
            return dataset_id

        except httpx.HTTPStatusError as e:
            print(f"HTTP Error: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    return None


async def run_evaluation(dataset_id: int) -> int | None:
    """Run evaluation on the mixed quality dataset."""
    print(f"\n[{get_msk_time()}] Running evaluation on dataset {dataset_id}...")

    payload = {"dataset_id": dataset_id, "metrics": ["faithfulness", "answer_relevancy"]}

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/evaluations/run", json=payload)
            response.raise_for_status()
            data = response.json()
            run_id: int | None = data.get("run_id")

            print(f"[{get_msk_time()}] Evaluation started. Run ID: {run_id}")

            # Polling for completion
            while True:
                status_res = await client.get(f"{BASE_URL}/evaluations/{run_id}")
                status_res.raise_for_status()
                status_data = status_res.json()

                status = status_data.get("status")
                print(f"[{get_msk_time()}] Status: {status}")

                if status in ["completed", "failed"]:
                    print(f"[{get_msk_time()}] Evaluation finished: {status}")
                    if status == "completed":
                        print_detailed_results(status_data, run_id)
                    break

                await asyncio.sleep(3)

            return run_id

        except httpx.HTTPStatusError as e:
            print(f"HTTP Error: {e.response.text}")
        except Exception as e:
            print(f"Error: {e}")
    return None


def get_score_emoji(score: float) -> str:
    """Get emoji based on score threshold."""
    if score >= 0.7:
        return "[PASS]"
    if score >= 0.5:
        return "[WARN]"
    return "[FAIL]"


def print_metric(metric_name: str, metric_data: dict) -> None:
    """Print a single metric result."""
    score = metric_data.get("score", 0.0)
    reason = metric_data.get("reason", "N/A")
    emoji = get_score_emoji(score)

    print(f"  {emoji} {metric_name}: {score:.2f}")
    print(f"     └─ {reason}")


def print_quality_group(quality: str, items: list) -> None:
    """Print results for a single quality tier."""
    if not items:
        return

    print(f"\n{'─' * 80}")
    quality_ranges = {"excellent": "0.9-1.0", "medium": "0.5-0.7", "poor": "0.0-0.3"}
    expected_range = quality_ranges.get(quality, "N/A")
    print(f"{quality.upper()} QUALITY ANSWER (Expected: {expected_range})")
    print("─" * 80)

    for idx, result in items:
        question = MIXED_QUALITY_DATASET["questions"][idx - 1]["question"]
        metrics = result.get("metrics", {})

        print(f"\nQ{idx}: {question}")

        for metric_name, metric_data in metrics.items():
            print_metric(metric_name, metric_data)


def print_summary_stats(stats: list) -> None:
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    for stat in stats:
        name = stat.get("name", "Unknown")
        avg = stat.get("avg_score", 0.0)
        pass_rate = stat.get("pass_rate", 0.0) * 100
        passed = stat.get("passed_count", 0)
        total = stat.get("total_count", 0)

        print(f"\n{name}:")
        print(f"   • Average Score: {avg:.2f}")
        print(f"   • Pass Rate: {pass_rate:.1f}% ({passed}/{total})")


def _group_results_by_question(results: list) -> dict[str, list]:
    """Group results by input text."""
    question_results: dict[str, list] = {}
    for result in results:
        input_text = result.get("input", "")
        if input_text not in question_results:
            question_results[input_text] = []
        question_results[input_text].append(result)
    return question_results


def _find_matching_results(question: str, question_results: dict[str, list]) -> list:
    """Find results matching a specific question."""
    for input_key, res_list in question_results.items():
        if question in input_key or input_key in question:
            return res_list
    return []


def _print_question_metrics(idx: int, q_data: dict, matching_results: list) -> None:
    """Print detailed metrics for a single question."""
    question = q_data["question"]
    expected_quality = q_data["expected_quality"]

    # Print question header
    quality_ranges = {"excellent": "0.9-1.0", "medium": "0.5-0.7", "poor": "0.0-0.3"}
    expected_range = quality_ranges.get(expected_quality, "N/A")

    print(f"\n{'─' * 80}")
    print(f"Q{idx} [{expected_quality.upper()}: Expected {expected_range}]")
    print(f"  {question}")
    print("\nAnswer:")
    print(f"  {q_data['answer'][:150]}...")
    print("\nMetrics:")

    # Print all metrics for this question
    for res in matching_results:
        metric_name = res.get("metric", "Unknown")
        score = res.get("score", 0.0)
        reason = res.get("reason", "N/A")
        emoji = get_score_emoji(score)

        print(f"  {emoji} {metric_name}: {score:.2f}")
        print(f"     └─ {reason}")


def _print_metrics_summary(stats: list) -> None:
    """Print overall summary statistics."""
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    if not stats:
        print("\nNo summary statistics available")
        return

    for stat in stats:
        name = stat.get("name", "Unknown")
        avg = stat.get("avg_score", 0.0)
        pass_rate = stat.get("pass_rate", 0.0) * 100
        passed = stat.get("passed_count", 0)
        total = stat.get("total_count", 0)

        print(f"\n{name}:")
        print(f"   • Average Score: {avg:.2f}")
        print(f"   • Pass Rate: {pass_rate:.1f}% ({passed}/{total})")


def print_detailed_results(status_data: dict, run_id: int) -> None:
    """Print detailed evaluation results grouped by expected quality."""
    print("\n" + "=" * 80)
    print(f"EVALUATION RESULTS - Run ID: {run_id}")
    print("=" * 80)

    results = status_data.get("results", [])
    if not results:
        print("No results found")
        return

    question_results = _group_results_by_question(results)

    # Match questions with expected quality
    print("\nDETAILED RESULTS:")
    for q_idx, q_data in enumerate(MIXED_QUALITY_DATASET["questions"]):
        question = q_data["question"]
        matching_results = _find_matching_results(question, question_results)

        if not matching_results:
            print(f"\nQ{q_idx + 1}: No results found for: {question[:50]}...")
            continue

        _print_question_metrics(q_idx + 1, q_data, matching_results)

    # Summary statistics
    _print_metrics_summary(status_data.get("metrics_stats", []))


async def main() -> None:
    print(f"Mixed Quality Evaluation Test - Started at {get_msk_time()} (MSK)")
    print("=" * 80)

    # Step 1: Create dataset
    dataset_id = await create_manual_dataset()
    if not dataset_id:
        print("Failed to create dataset")
        sys.exit(1)

    # Step 2: Run evaluation
    print(f"\n[{get_msk_time()}] Waiting 5 seconds before evaluation...")
    await asyncio.sleep(5)

    run_id = await run_evaluation(dataset_id)
    if not run_id:
        print("Evaluation failed")
        sys.exit(1)

    print(f"\n[{get_msk_time()}] Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
