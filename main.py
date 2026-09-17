from fastapi import FastAPI

import inngest
from inngest.fast_api import serve

from functions import client, say_hello


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


serve(
    app,
    client,
    [say_hello],
)
