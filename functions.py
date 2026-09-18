import asyncio
from datetime import timedelta

import inngest
from dotenv import load_dotenv

from report_engine.render import generate_report
from report_store import reports


load_dotenv()


client = inngest.Inngest(
    app_id="healthcare-report-job-queue",
)


async def build_report(report_id: str, topic: str):
    if topic == "fail":
        raise RuntimeError("Intentional report generation failure")

    result = await asyncio.to_thread(generate_report, report_id)

    return {
        "report_id": report_id,
        "topic": topic,
        "summary": f"Biomedical equipment maintenance report generated for: {topic}",
        "file": result["file"],
        "total_reports": result["total_reports"],
        "average_confidence": result["average_confidence"],
    }


async def restart_step_one():
    return "step one complete"


async def restart_step_three():
    return "step three complete"


@client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context):
    await ctx.step.sleep("wait-before-response", timedelta(seconds=5))
    return "Hello from the background!"


async def mark_report_failed(ctx: inngest.Context):
    report_id = ctx.event.data.get("event", {}).get("data", {}).get("id")

    if report_id and report_id in reports:
        reports[report_id]["status"] = "failed"
        reports[report_id]["error"] = "Report generation failed after retries"

    return {"status": "failed", "report_id": report_id}


@client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    idempotency="event.data.id",
    retries=2,
    concurrency=[{"limit": 2}],
    on_failure=mark_report_failed,
)
async def make_report(ctx: inngest.Context):
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    existing_report = reports.get(report_id)

    # Application-level idempotency backup:
    # completed or permanently failed reports do not run again.
    # Pending reports remain eligible so Inngest retries can continue normally.
    if existing_report and existing_report.get("status") == "done":
        return existing_report["result"]

    if existing_report and existing_report.get("status") == "failed":
        return {
            "status": "failed",
            "report_id": report_id,
            "error": existing_report.get(
                "error",
                "Report generation failed after retries",
            ),
        }

    await ctx.step.sleep("do-the-slow-work", timedelta(seconds=8))

    result = await ctx.step.run(
        "build-report",
        build_report,
        report_id,
        topic,
    )

    reports[report_id]["status"] = "done"
    reports[report_id]["result"] = result

    return result


@client.create_function(
    fn_id="restart-proof",
    trigger=inngest.TriggerEvent(event="restart/test"),
)
async def restart_proof(ctx: inngest.Context):
    step_one = await ctx.step.run(
        "step-one",
        restart_step_one,
    )

    await ctx.step.sleep(
        "step-two",
        timedelta(seconds=8),
    )

    step_three = await ctx.step.run(
        "step-three",
        restart_step_three,
    )

    return {
        "status": "completed",
        "step_one": step_one,
        "step_three": step_three,
    }


@client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context):
    counts = {
        "pending": 0,
        "done": 0,
        "failed": 0,
    }

    for report in reports.values():
        status = report.get("status")
        if status in counts:
            counts[status] += 1

    print(
        "Heartbeat:",
        f"pending={counts['pending']}",
        f"done={counts['done']}",
        f"failed={counts['failed']}",
    )

    return counts
