import inngest
from dotenv import load_dotenv


load_dotenv()


client = inngest.Inngest(
    app_id="healthcare-report-job-queue",
)


@client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context):
    await ctx.step.sleep("wait-before-response", 5)
    return "Hello from the background!"
