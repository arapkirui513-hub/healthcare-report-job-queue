import asyncio
import inngest
from dotenv import load_dotenv

load_dotenv()

client = inngest.Inngest(app_id="healthcare-report-job-queue")


async def main():
    event = inngest.Event(
        name="restart/test",
        data={},
    )
    await client.send(event)
    print("Sent restart/test event")


if __name__ == "__main__":
    asyncio.run(main())