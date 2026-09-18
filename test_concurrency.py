import asyncio
import json
import urllib.request

URL = "http://localhost:8000/reports"

def create_report(number):
    payload = json.dumps({
        "topic": f"Concurrency Test Report {number}"
    }).encode()

    request = urllib.request.Request(
        URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        body = json.loads(response.read().decode())
        return response.status, body

async def main():
    results = await asyncio.gather(
        *(asyncio.to_thread(create_report, i) for i in range(1, 6))
    )

    print("=== CONCURRENCY TEST ===")
    for status, body in results:
        print(f"Status: {status}")
        print(f"ID: {body['id']}")
        print(f"Topic: {body['topic']}")
        print(f"Initial status: {body['status']}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
