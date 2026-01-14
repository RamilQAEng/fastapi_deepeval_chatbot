import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

# Constants
BASE_URL = "http://127.0.0.1:8000/api/v1"
MSK_TZ = ZoneInfo("Europe/Moscow")


def get_msk_time() -> str:
    return datetime.now(MSK_TZ).isoformat()


async def verify_upload() -> None:
    print(f"\n[{get_msk_time()}] --- STARTING PRE-GENERATED DATASET UPLOAD TEST ---")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Get Template
        print(f"[{get_msk_time()}] Fetching template...")
        resp = await client.get(f"{BASE_URL}/template")
        resp.raise_for_status()
        template = resp.json()

        # 2. Prepare Payload (Modify template slightly)
        payload = template
        payload["test_cases"][0]["input"] = "What is the capital of France?"
        payload["test_cases"][0]["actual_output"] = "Paris"
        payload["test_cases"][0]["expected_output"] = "Paris"
        payload["test_cases"][0]["context"] = ["Paris is the capital of France."]
        payload["test_cases"][0]["retrieval_context"] = ["Paris is the capital of France."]

        # Add a second case
        payload["test_cases"].append(
            {
                "input": "What is 2+2?",
                "actual_output": "4",
                "expected_output": "4",
                "context": ["Basic math: 2 plus 2 equals 4."],
                "retrieval_context": ["Basic math rules."],
            }
        )

        print(f"[{get_msk_time()}] Uploading payload with run_eval=True...")
        # 3. Upload with run_eval=True
        resp = await client.post(f"{BASE_URL}/datasets/upload?run_eval=true", json=payload)
        resp.raise_for_status()
        data = resp.json()

        print(f"[{get_msk_time()}] Response: {json.dumps(data, indent=2)}")

        eval_run_id = data.get("eval_run_id")
        if not eval_run_id:
            print("Error: No eval_run_id returned!")
            return

        print(f"[{get_msk_time()}] Evaluation triggered. Run ID: {eval_run_id}")

        # 4. Poll for results
        while True:
            status_res = await client.get(f"{BASE_URL}/evaluations/{eval_run_id}")
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


if __name__ == "__main__":
    asyncio.run(verify_upload())
