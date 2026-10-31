# design_it_backend

FastAPI service that makes every LLM call for [design_it](https://github.com/davidgohzk/design_it). The frontend never talks to SoCLaaS directly: it calls this backend, which adds the system prompts, model and sampling parameters, and holds the API key.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | none | `{"status":"ok"}`, used by the Render health check and the frontend warm-up ping |
| GET | `/health/upstream` | none | `{"reachable","status","latency_ms"}`, checks that this host can reach SoCLaaS |
| POST | `/api/chat` | `{"caseId","messages":[{"role":"user"\|"assistant","content"}]}` | SSE stream in Mei's persona. `caseId` is `"community-room"` (Community Room, /demo). |
| POST | `/api/assess` | `{"caseId","task":"match"\|"assertion"\|"justify"\|"fit"\|"suggest"\|"bano"\|"turns"\|"scenario_adequacy"\|"rationale"\|"iso","facts","evidence","retrySections"?}` | `{"content": "<raw model JSON>","model","promptVersion"}`: one step of the review. `facts` must carry this case's fact ids exactly; the browser parses and verifies the model's JSON |

**Streams.** Each stream sends `data: {"delta":"..."}` events and ends with `event: done`, whose data is `{"model"}`. A failure after streaming has started is sent as `event: error` with `data: {"code","message"}`.

**Prompt versions.** `promptVersion` is set only for the tasks listed in `ASSESS_PROMPT_VERSIONS`
(`bano`, `turns`, `scenario_adequacy`, `rationale` and `iso`), and is `null` for the rest. It is stored on the
frontend's result so a saved review says which judge prompt produced it. The `bano` task judges the
items of the interview-mistake checklist that no rule can decide; it is teaching feedback, so its
prompt forbids returning any count, score or rating.

**Errors.** Every other error is a JSON body `{"error":{"code","message"}}` with a matching HTTP status.

**Limits.**
- 20 requests a minute and 300 a day per IP.
- 6 concurrent upstream calls.
- Request bodies up to 512 KB.
- CORS allows the origins in `ALLOWED_ORIGINS` (`*`, the default in `render.yaml`, allows any origin).

## Where things live

One package per feature. Each owns its own route, request models and prompts, so a change to one AI
call touches one directory. Everything they share sits at the top level.

| Path | What it owns |
| --- | --- |
| `app/main.py` | The app factory: settings, shared state, middleware, error shape, routers |
| `app/middleware.py` | Body-size limit and validation-error wording |
| `app/health.py` | `/`, `/health`, `/health/upstream` — nothing here asks for a completion |
| `app/llm.py` | The only module that touches the model SDK: streaming, completions, timeouts, error translation, the concurrency cap |
| `app/config.py` `app/errors.py` `app/ratelimit.py` | Settings from env, the `{error:{...}}` shape, the per-IP sliding window |
| `app/schemas.py` | `StrictModel`, the `extra=forbid` base every request model uses |
| `app/cases/` | Case content: the facts JSON and its loader, `CaseId` |
| `app/chat/` | `/api/chat`: the persona prompt, the structured client, and the disclosure guard |
| `app/assess/` | `/api/assess`: the route, its schemas, the task contract and the judge prompts |
| `app/assess/prompts/` | **One file per judge task**, each holding its `PROMPT`, `SECTION` and `VERSION` |

`app/assess/prompts/__init__.py` assembles `ASSESS_PROMPTS`, `ASSESS_SECTIONS` and
`ASSESS_PROMPT_VERSIONS` from those ten modules rather than repeating their keys, so the registries
cannot drift from the prompts they describe. Changing a prompt means bumping `VERSION` in the same
file, in the same edit.

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # fill in SOCLAAS_API_KEY and SOCLAAS_MODEL
pytest
uvicorn app.main:app --reload --port 8000 --env-file .env
```

```bash
curl -N -X POST localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"caseId":"community-room","messages":[{"role":"user","content":"Hi Mei, what happens when someone books a room?"}]}'
```

## Deploying on Render

The service is defined in `render.yaml`.
1. Set `SOCLAAS_API_KEY` and `SOCLAAS_MODEL` in the Render dashboard.
2. After deploying, open `https://<service>.onrender.com/health/upstream`. If it shows `"reachable": false`, Render cannot reach the SoCLaaS gateway.

Free instances sleep after about 15 minutes of inactivity. The first request after that can take around a minute.

The interview persona lives in `app/chat/prompts.py`, and each judge prompt in its own file under `app/assess/prompts/`. Each case's facts come from `app/cases/<case>.facts.json`; the frontend keeps an identical copy in `src/cases/<case>/facts.json`, and both repos test their cases against it (`tests/test_facts_sync.py` here, `src/cases/facts.sync.test.ts` there). Change a facts file in both repos together. `PERSONAS` (in `app/chat/prompts.py`) maps each `caseId` to its persona prompt and facts. The `/api/assess` task list is mirrored the same way: `app/assess/tasks.json` here, `src/review/judge/tasks.json` there, compared by a test on each side (`tests/test_tasks_contract.py`).
