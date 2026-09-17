from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import inngest
from inngest.fast_api import serve

from functions import client, heartbeat, make_report, say_hello
from report_store import reports


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports")
async def create_report(payload: dict):
    topic = payload.get("topic")

    if not topic or not isinstance(topic, str) or not topic.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "topic is required"},
        )

    topic = topic.strip()
    report_id = str(uuid4())

    report = {
        "id": report_id,
        "topic": topic,
        "status": "pending",
    }

    reports[report_id] = report

    await client.send(
        inngest.Event(
            name="report/requested",
            data={
                "id": report_id,
                "topic": topic,
            },
        )
    )

    return JSONResponse(
        status_code=202,
        content=report,
    )


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    report = reports.get(report_id)

    if report is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "report not found"},
        )

    return report


serve(
    app,
    client,
    [say_hello, make_report, heartbeat],
)
