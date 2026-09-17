import asyncio

import inngest

from functions import client


async def main():
    event = inngest.Event(
        name="test/hello",
        data={},
    )

    result = await client.send(event)
    print("Event sent:", result)


if __name__ == "__main__":
    asyncio.run(main())
