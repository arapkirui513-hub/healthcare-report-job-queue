import asyncio
import json
import urllib.request

import inngest

from functions import client


def create_report():
    request = urllib.request.Request(
        "http://localhost:8000/reports",
        data=json.dumps({
            "topic": "Idempotency Verification - Biomedical Equipment Maintenance"
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


async def main():
    report = create_report()
    report_id = report["id"]

    print("Original report:")
    print(json.dumps(report, indent=2))

    print("\nWaiting for original job...")
    await asyncio.sleep(12)

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
