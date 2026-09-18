import asyncio
import json
import urllib.request

import inngest

from functions import client


BASE_URL = "http://localhost:8000"


def request_json(url, method="GET", payload=None):
    data = None

    if payload is not None:
        data = json.dumps(payload).encode()

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def create_report():
    return request_json(
        f"{BASE_URL}/reports",
        method="POST",
        payload={
            "topic": "Idempotency Verification - Biomedical Equipment Maintenance"
        },
    )


async def wait_for_completion(report_id):
    for attempt in range(30):
        report = request_json(f"{BASE_URL}/reports/{report_id}")

        print(
            f"Poll {attempt + 1}: "
            f"status={report['status']}"
        )

        if report["status"] in {"done", "failed"}:
            return report

        await asyncio.sleep(2)

    raise TimeoutError("Report did not complete within 60 seconds")


async def main():
    report = create_report()
    report_id = report["id"]

    print("Original report:")
    print(json.dumps(report, indent=2))

    print("\nWaiting for original job to complete...")
    final_report = await wait_for_completion(report_id)

    print("\nOriginal job result:")
    print(json.dumps(final_report, indent=2))

    if final_report["status"] != "done":
        raise RuntimeError(
            f"Original report did not complete successfully: "
            f"{final_report['status']}"
        )

    duplicate_event = inngest.Event(
        name="report/requested",
        data={
            "id": report_id,
            "topic": report["topic"],
        },
    )

    result = await client.send(duplicate_event)

    print("\nDuplicate event sent:")
    print(result)

    print("\nShared report ID:")
    print(report_id)


if __name__ == "__main__":
    asyncio.run(main())
