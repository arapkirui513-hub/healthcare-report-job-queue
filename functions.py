import asyncio
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


@client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context):
    await ctx.step.sleep("wait-before-response", 5)
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
    on_failure=mark_report_failed,
)
async def make_report(ctx: inngest.Context):
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

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
