# design_it_backend

FastAPI service that makes every LLM call for [design_it](https://github.com/davidgohzk/design_it). The frontend never talks to SoCLaaS directly: it calls this backend, which adds the system prompts, model and sampling parameters, and holds the API key.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | none | `{"status":"ok"}`, used by the Render health check and the frontend warm-up ping |
| GET | `/health/upstream` | none | `{"reachable","status","latency_ms"}`, checks that this host can reach SoCLaaS |
| POST | `/api/chat` | `{"caseId","messages":[{"role":"user"\|"assistant","content"}]}` | SSE stream in Mei's persona. `caseId` is `"community-room"` (Community Room, /demo). |
| POST | `/api/diagram` | `{"prompt","currentCode"?,"context"?,"priorAttempt"?:{"code","error"}}` | SSE stream (Mermaid source) from the diagram helper. `currentCode` is its last diagram, which the prompt edits; `context` lists the node IDs and labels used in the doc's sketches, one per line |
| POST | `/api/assess` | `{"caseId","task":"match"\|"assertion"\|"justify"\|"fit"\|"suggest"\|"bano","facts","evidence","retrySections"?}` | `{"content": "<raw model JSON>","model","promptVersion"}`: one step of the review. `facts` must carry this case's fact ids exactly; the browser parses and verifies the model's JSON |

**Streams.** Each stream sends `data: {"delta":"..."}` events and ends with `event: done`, whose data is `{"model"}`. A failure after streaming has started is sent as `event: error` with `data: {"code","message"}`.

**Prompt versions.** `promptVersion` is set only for the tasks listed in `ASSESS_PROMPT_VERSIONS`
(today just `bano`, at `BANO_PROMPT_VERSION`), and is `null` for the rest. It is stored on the
frontend's result so a saved review says which judge prompt produced it. The `bano` task judges the
items of the interview-mistake checklist that no rule can decide; it is teaching feedback, so its
prompt forbids returning any count, score or rating.

**Errors.** Every other error is a JSON body `{"error":{"code","message"}}` with a matching HTTP status.

**Limits.**
- 20 requests a minute and 300 a day per IP.
- 6 concurrent upstream calls.
- Request bodies up to 512 KB.
- CORS allows the origins in `ALLOWED_ORIGINS` (`*`, the default in `render.yaml`, allows any origin).

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

The system prompts live in `app/prompts.py`. Each case's facts come from `app/cases/<case>.facts.json`; the frontend keeps an identical copy in `src/cases/<case>/facts.json`, and both repos test their cases against it (`tests/test_facts_sync.py` here, `src/cases/facts.sync.test.ts` there). Change a facts file in both repos together. `PERSONAS` maps each `caseId` to its persona prompt and facts.
