import inngest
from dotenv import load_dotenv

from report_store import reports


load_dotenv()


client = inngest.Inngest(
    app_id="healthcare-report-job-queue",
)


async def build_report(report_id: str, topic: str):
    if topic == "fail":
        raise RuntimeError("Intentional report generation failure")

    return {
        "report_id": report_id,
        "topic": topic,
        "summary": f"Background report generated for: {topic}",
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
    retries=2,
    on_failure=mark_report_failed,
)
async def make_report(ctx: inngest.Context):
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    await ctx.step.sleep("do-the-slow-work", 8)

    result = await ctx.step.run(
        "build-report",
        build_report,
        report_id,
        topic,
    )

    reports[report_id]["status"] = "done"
    reports[report_id]["result"] = result

    return result
