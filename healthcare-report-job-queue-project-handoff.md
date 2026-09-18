# Healthcare Report Job Queue – Complete Project Context & Interview Handoff

This companion file mirrors the DOCX handoff. The DOCX is the primary formatted version.

Healthcare Report Job Queue – Complete Project Context & Interview Handoff

FlyRank Internship · Backend AI Engineering · Week 7 portal / W4 A7 assignment naming

Purpose: This document is a durable handoff for future study, debugging, portfolio review, and interview preparation. A future LLM should be able to read it and reconstruct what was built, why it was built that way, what changed during implementation, what was verified, what was not fully proven, and what the final repository contains.

1. Executive summary

This project is a FastAPI + Inngest background-job system for generating biomedical equipment maintenance reports. The central pattern is: accept a request, return HTTP 202 with a report ID and pending status, perform slow work in an Inngest background function, and expose GET /reports/{id} so the client can observe pending, done, or failed state.

The original assignment was intentionally small and synthetic. It was later extended with a real biomedical maintenance report-generation pipeline using SQLite data, aggregation, HTML generation, Playwright, system Google Chrome, and A4 PDF output. The final project also includes retries, failure handling, Inngest-native idempotency, an application-level status guard, function-level concurrency limit 2, a cron heartbeat, and a three-step durable restart demonstration.

Final public repository: https://github.com/arapkirui513-hub/healthcare-report-job-queue

2. Assignment context and naming

The uploaded assignment PDF calls the work FlyRank Internship · Backend Track · W4 · A7 – Your first background job. The submission portal later displayed When: Week 7. Treat this as a naming discrepancy between the portal and the PDF, not as two different projects.

The assignment required FastAPI or Node/Express, Inngest, a fast 202 response, approximately 8-second background work, a status endpoint, retries, an intentional failure path, 400 validation, a one-minute cron heartbeat, a public GitHub repository, README evidence, idempotency, concurrency limit 2, and a durable restart experiment. It also contained optional/bonus material such as the AI rematch.

3. Stage 0 – FastAPI foundation

The project began with a minimal FastAPI service and a health endpoint on port 8000.

GET /health\n{"status": "ok"}

This established the HTTP server before introducing Inngest.

4. Stage 1 – Inngest

The first background function was say-hello, triggered by test/hello. It used a durable 5-second sleep. The Inngest function endpoint was served at /api/inngest, with the local development dashboard on port 8288.

FastAPI: python -m uvicorn main:app --reload --port 8000\nInngest: npx inngest-cli@latest dev -u http://localhost:8000/api/inngest\nDashboard: http://localhost:8288

5. Stage 2 – background report workflow

The next stage introduced an in-memory reports dictionary. POST /reports validates topic, creates a UUID, stores a pending report, sends report/requested, and returns HTTP 202.

POST /reports\n{"topic": "Biomedical Equipment Maintenance Operations Report"}\n\n→ 202 Accepted\n{"id": "<uuid>", "topic": "...", "status": "pending"}

make-report receives the event, performs an 8-second durable Inngest sleep, then runs build-report. The result is stored and the report becomes done. GET /reports/{id} returns the current state, while an unknown ID returns 404.

The key lesson is separation of responsibilities: the HTTP request creates the job and returns; the worker owns expensive work; the status endpoint lets the caller observe progress.

6. Stage 3 – validation, retries, and failure

Missing or invalid topic is rejected immediately with 400 and no background event is sent. The topic fail intentionally raises an exception inside report generation.

retries=2\n\ntopic == "fail"\n→ raise RuntimeError("Intentional report generation failure")

retries=2 means the initial attempt plus two retries, for three total attempts. The final failure triggers on_failure, which marks the report failed.

The fresh regression trace showed Attempt 0 = 8.084s, Attempt 1 = 16.887s, Attempt 2 = 53.506s, and do-the-slow-work = 8.071s. The separate failure-handler run then completed and returned the failed report ID.

7. Stage 4 – cron heartbeat

The heartbeat function uses an every-minute cron trigger and counts pending, done, and failed reports.

@client.create_function(\n    fn_id="heartbeat",\n    trigger=inngest.TriggerCron(cron="* * * * *"),\n)

The README documents 0 8 * * * for every day at 08:00 and 0 22 * * 0 for every Sunday at 22:00.

8. Phase B – real biomedical report-generation pipeline

After the basic A7 workflow was working, the simulated report build was replaced by a real biomedical maintenance report-generation pipeline.

The pipeline uses a checked-in SQLite database containing 200 synthetic maintenance reports. The query layer aggregates the data. The renderer builds HTML and converts it to A4 PDF using Playwright and the system Google Chrome browser.

result = await asyncio.to_thread(generate_report, report_id)

The asyncio.to_thread wrapper was used because the Playwright rendering path is synchronous and needed to operate correctly in the Windows/Inngest execution environment.

A verified end-to-end run produced a 67,592-byte PDF, total_reports=200, and average_confidence=0.884.

9. A6/A8 naming ambiguity and decision

During implementation there was uncertainty about portal A6/A8 naming versus the technical PDF. The decision was to follow the actual PDF specification for the background-job assignment and treat the real biomedical report engine as a Phase B extension. This avoided redesigning the project around ambiguous portal wording.

The result is a genuine aggregation-to-PDF pipeline rather than a description-only integration.

10. Important limitation – request latency

The assignment target says POST /reports should return 202 + an ID in under one second. The final Phase B measurement was approximately 2.04 seconds. The request nevertheless returned 202 with pending before the background report completed.

Interview rule: never claim that sub-second latency was proven. The accurate statement is that the endpoint returned before the slow report-generation workflow completed, while the measured local Phase B request was about 2.04 seconds.

11. The 8-second sleep investigation

A previously captured screenshot appeared to show do-the-slow-work at about 148ms. This raised a legitimate concern that the configured 8-second sleep might not actually be running.

Instead of guessing, the existing polling test was rerun. It polls every two seconds and produced Poll 1 pending, Poll 2 pending, Poll 3 pending, Poll 4 done. More decisively, the fresh failure regression trace showed do-the-slow-work at 8.071 seconds.

Conclusion: the current implementation performs the 8-second sleep. The earlier 148ms trace should be treated as an older/anomalous execution, not as the current behavior.

12. Final idempotency design

The primary mechanism is Inngest-native idempotency:

idempotency="event.data.id"

The report UUID is the idempotency key. A duplicate report/requested event with the same ID is prevented from creating another make-report execution within the configured 24-hour idempotency window.

A secondary application-level terminal-state guard was added before the slow work:

existing_report = reports.get(report_id)\n\nif existing_report and existing_report.get("status") == "done":\n    return existing_report["result"]\n\nif existing_report and existing_report.get("status") == "failed":\n    return {\n        "status": "failed",\n        "report_id": report_id,\n        "error": existing_report.get(\n            "error",\n            "Report generation failed after retries",\n        ),\n    }

Pending reports are intentionally allowed through so Inngest retries are not blocked. This guard is therefore a secondary terminal-state protection, not a replacement for retries.

The runtime test created a real report, waited for done, sent the same report/requested event again with the same report ID, and observed no second make-report execution in the Inngest run history.

13. Concurrency

make-report uses a function-level concurrency limit of 2:

concurrency=[{"limit": 2}]

Five report/requested events were submitted concurrently. The dashboard showed five corresponding make-report executions and the configuration panel confirmed function scope with limit 2.

The exact moment of two active and three waiting jobs was not clearly visible in the screenshot, so the README deliberately does not claim that stronger runtime observation. Configuration evidence is strong; exact queue-depth evidence was not claimed.

14. Durable restart experiment

restart-proof contains three steps: step-one, an 8-second durable step-two sleep, and step-three.

step_one = await ctx.step.run("step-one", restart_step_one)\n\nawait ctx.step.sleep(\n    "step-two",\n    timedelta(seconds=8),\n)\n\nstep_three = await ctx.step.run(\n    "step-three", restart_step_three,\n)

FastAPI was stopped while the workflow was running and restarted while the Inngest Development Server remained alive. The existing execution resumed and completed later steps. The trace retained the completed step-one checkpoint rather than creating a second step-one execution.

The trace showed step-one 91ms, step-two 8.000s, step-three 1m 31s, and finalization 121ms. The long total duration reflects the restart gap.

15. Storage limitation

Application report state is stored in an in-memory Python dictionary. Restarting FastAPI therefore clears report records. Inngest workflow execution can remain durable, but the application's own report-state dictionary is not durable.

For production, move report state to PostgreSQL or another durable application store.

report.db is different: it is a checked-in synthetic fixture containing 200 maintenance-report records, intentionally committed so the report-generation pipeline is reproducible immediately after cloning without a separate seed step.

16. Key files

17. Final Git history

af93dc8  Complete A7 documentation evidence
cbdc684  Add failure retry regression evidence
3c85c20  Harden report idempotency and document runtime evidence
d2cacd9  Complete A7 background job and report pipeline
ba9a7a6  Phase B: integrate real biomedical report generation
fdbe026  Add report job idempotency
c2628b5  Document HTTP validation evidence
592184d  Clarify retry evidence and rename screenshots
2080283  Stage 5: polish README and add execution evidence
e9c1ac8  Stage 4: add cron heartbeat
0138db4  Stage 3: add retries and failure handling
a9f7187  Stage 2: add background report jobs
dee57c5  Stage 1: add Inngest background function
12f5491  Stage 0: hello server

18. Final verified behavior

FastAPI health endpoint – verified.

Inngest Dev Server and dashboard – verified.

POST /reports returns 202 with pending state – verified.

GET /reports/{id} supports pending/done/failed – verified.

Unknown report ID returns 404 – verified.

Missing topic returns 400 and no event – verified.

make-report has durable sleep and build-report step – verified.

8-second slow step – verified by fresh dashboard trace and polling.

retries=2 gives three total attempts – verified.

on_failure handler – verified.

Every-minute heartbeat – verified.

Inngest-native idempotency – verified.

Application-level terminal-state guard – implemented and normal-completion regression tested.

Concurrency limit 2 – configuration verified.

Durable three-step restart – verified.

Real biomedical PDF pipeline – verified.

Synthetic database fixture – committed.

README and public GitHub repository – completed.

Final Git working tree – clean.

19. What is not fully proven and must be stated honestly

1. Sub-second POST latency was not proven; the measured Phase B request was approximately 2.04 seconds.

2. Exact runtime queue depth of two active plus three waiting jobs was not proven from the screenshot; only the function-level limit of 2 and five submitted jobs were verified.

3. Application report state is not durable across FastAPI restarts because it is in memory.

4. The AI rematch/AI-vs-me section was optional/bonus and was not part of the core final deliverable.

20. 60-second interview explanation

I built a FastAPI and Inngest background-job system for biomedical maintenance reports. The API validates the request, creates a report record, emits a report/requested event, and returns 202 with a pending ID instead of waiting for slow work. Inngest handles the workflow with an 8-second durable step followed by a report-building step that queries 200 synthetic maintenance records and renders an A4 PDF with Playwright. I added retries, an on-failure handler, Inngest-native idempotency plus an application-level terminal-state guard, a function concurrency limit of two, a cron heartbeat, and a three-step restart experiment. The restart experiment showed that completed workflow steps survive an application restart. The main production limitation is that application report state is still in memory, so I would move that to PostgreSQL.

21. Interview questions and answers

Q: Why return 202 instead of the final report?

A: Because report generation is slow. The request should create the job and return control while the worker performs expensive work.

Q: Why use Inngest?

A: It provides event-triggered background functions, durable steps, retries, concurrency controls, cron scheduling, and a dashboard for observing executions.

Q: Why use step.sleep instead of asyncio.sleep?

A: The assignment was teaching durable background work. Inngest's step.sleep participates in the workflow model and is visible in execution traces.

Q: Why both Inngest idempotency and an application guard?

A: Inngest-native idempotency is primary duplicate-event protection. The application guard protects terminal report state. Pending reports remain eligible for retries.

Q: Why did the failure test take a long time?

A: There were three attempts and backoff between retries. The trace showed about 8.084s, 16.887s, and 53.506s.

Q: What does durable mean?

A: Workflow state is preserved at step boundaries. After FastAPI restarted, the completed step-one checkpoint remained and the workflow resumed with later steps.

Q: What happens to report state if FastAPI restarts?

A: The in-memory reports dictionary is cleared. That is a known limitation.

Q: Why is report.db committed?

A: It is a synthetic 200-row fixture. Committing it makes the report-generation pipeline reproducible after cloning.

Q: What would you improve for production?

A: Move report state to PostgreSQL, make artifact storage durable, improve request-path latency toward the assignment target, and add appropriate security controls.

22. Reproducing the project

Use the repository README as the operational source of truth. A fresh environment needs Python 3.13+, the Python dependencies, Google Chrome, Node.js/npm, the checked-in report.db, and the Inngest Dev Server.

git clone https://github.com/arapkirui513-hub/healthcare-report-job-queue.git
cd healthcare-report-job-queue

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Terminal 1
python -m uvicorn main:app --reload --port 8000

# Terminal 2
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest

# Dashboard
http://localhost:8288

23. Guidance for another LLM

If another LLM receives this document, it should preserve these facts and not invent stronger claims:

Final repo: arapkirui513-hub/healthcare-report-job-queue.

Architecture: FastAPI + Inngest.

Real pipeline: SQLite → aggregation → HTML → Playwright/system Chrome → A4 PDF.

report.db contains 200 synthetic maintenance records.

Fresh do-the-slow-work evidence was 8.071s.

retries=2 means three total attempts.

Idempotency has Inngest-native and application-level terminal-state protection.

Concurrency limit 2 is configured and verified; exact queue depth was not claimed.

Durable three-step restart was genuinely demonstrated.

Final Phase B POST measurement was about 2.04s, so sub-second latency must not be claimed.

Application report state remains in memory.

A6/A8 naming ambiguity was handled by following the technical PDF and treating the report engine as a Phase B extension.

24. Source and evidence note

The assignment requirements summarized here are based on the uploaded FlyRank “Your first background job” PDF. The implementation and verification details are based on the project code, terminal outputs, Inngest dashboard screenshots, Git history, and final README. The assignment specifically required the 202/poll proof, retries, cron, public repo, idempotency, concurrency, and durable restart evidence.
