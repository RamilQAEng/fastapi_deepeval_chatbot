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


async def test_generation() -> int | None:  # noqa: PLR0911
    print(f"\n[{get_msk_time()}] --- STARTING TEST 1: GENERATION ---")

    test_text = """POLICIES: CUSTOMER RETENTION & SALES OBJECTIONS

1. Handling Price Objections:
If a customer claims they found a cheaper offer for the 'SilverModel S' elsewhere,
do not immediately discount. First, emphasize the 'Total Care' warranty included
in our price (valued at $2,000). If the customer still insists on cancelling,
the manager is authorized to offer a 3% discount or free winter tires.

2. Trade-In Retention:
If a customer is unhappy with the trade-in value, explain that our valuation
includes a 'Convenience Fee' waiver. We can increase trade-in value by up to $500
if the customer commits to financing with our partner bank.

3. Post-Sale Anxiety (Cold Feet):
Customers calling to cancel within 24 hours often have 'buyer's remorse'.
The agent must schedule a video call to demonstrate the car's features again.
Do not process cancellation over the phone/email without a verbal confirmation
from the retention specialist."""

    payload = {
        "text": test_text,
        "num_questions": 2,
    }

    print(f"[{get_msk_time()}] Request Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    start_time = datetime.now()
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/datasets/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            print(f"[{get_msk_time()}] Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"[{get_msk_time()}] Generation took {duration:.2f} seconds.")

            dataset_id: int | None = data.get("dataset_id")
            if not dataset_id:
                print("ERROR: No dataset ID returned!")
                sys.exit(1)

            # Fetch actual content to verify
            print(f"[{get_msk_time()}] Fetching created dataset content...")
            dataset_res = await client.get(f"{BASE_URL}/datasets/{dataset_id}")
            dataset_res.raise_for_status()
            dataset_data = dataset_res.json()
            print(f"[{get_msk_time()}] DATASET CONTENT:")
            print(json.dumps(dataset_data, indent=2, ensure_ascii=False))

            return dataset_id

        except httpx.HTTPStatusError as e:
            print(f"HTTP Error: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    return None


async def test_evaluation(dataset_id: int) -> int | None:
    print(f"\n[{get_msk_time()}] --- STARTING TEST 2: EVALUATION (Chained) ---")
    print(f"Using Dataset ID: {dataset_id}")

    payload = {"dataset_id": dataset_id, "metrics": ["faithfulness", "answer_relevancy"]}

    print(f"[{get_msk_time()}] Request Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for eval
        try:
            response = await client.post(f"{BASE_URL}/evaluations/run", json=payload)
            response.raise_for_status()
            data = response.json()
            run_id: int | None = data.get("run_id")
            print(f"[{get_msk_time()}] Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            print(f"[{get_msk_time()}] Evaluation triggered. Run ID: {run_id}")

            # Polling for completion
            while True:
                status_res = await client.get(f"{BASE_URL}/evaluations/{run_id}")
                status_res.raise_for_status()
                status_data = status_res.json()

                status = status_data.get("status")
                print(f"[{get_msk_time()}] Status: {status}")

                if status in ["completed", "failed"]:
                    print(f"[{get_msk_time()}] Evaluation finished with status: {status}")
                    if status == "completed":
                        print(f"[{get_msk_time()}] RESULTS:")
                        print(json.dumps(status_data.get("results"), indent=2, ensure_ascii=False))
                    break

                await asyncio.sleep(2)

            return run_id

        except httpx.HTTPStatusError as e:
            print(f"HTTP Error: {e.response.text}")
        except Exception as e:
            print(f"Error: {e}")
    return None


async def main() -> None:
    print(f"Script started at {get_msk_time()} (MSK)")

    # Run Test 1
    dataset_id = await test_generation()

    # Run Test 2
    if dataset_id:
        print(f"\n[{get_msk_time()}] Waiting 10 seconds to respect Rate Limits...")
        await asyncio.sleep(10)
        await test_evaluation(dataset_id)

    print(f"\n[{get_msk_time()}] Tests completed.")


if __name__ == "__main__":
    asyncio.run(main())
