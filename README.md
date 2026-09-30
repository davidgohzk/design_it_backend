# design_it_backend

FastAPI service that makes every LLM call for [design_it](https://github.com/davidgohzk/design_it). The frontend never talks to SoCLaaS directly: it calls this backend, which adds the system prompts, model and sampling parameters, and holds the API key.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/health` | none | `{"status":"ok"}`, used by the Render health check and the frontend warm-up ping |
| GET | `/health/upstream` | none | `{"reachable","status","latency_ms"}`, checks that this host can reach SoCLaaS |
| POST | `/api/chat` | `{"caseId"?,"messages":[{"role":"user"\|"assistant","content"}]}` | SSE stream in the case's persona. `caseId` is `"brightpath"` (Sarah, the default) or `"community-room"` (Mei) |
| POST | `/api/diagram` | `{"prompt","currentCode"?,"priorAttempt"?:{"code","error"}}` | SSE stream (Mermaid source) |
| POST | `/api/review` | `{"coverageChecklist","caseBrief","transcript","soapReport","extractedReferences"}` | `{"content": "<raw model JSON>"}` |

**Streams.** Each stream sends `data: {"delta":"..."}` events and ends with `event: done`, whose data is `{"promptVersion","model"}`. A failure after streaming has started is sent as `event: error` with `data: {"code","message"}`.

**Errors.** Every other error is a JSON body `{"error":{"code","message"}}` with a matching HTTP status.

**Using your own key.** Send `X-SoCLaaS-Key: <key>` to use that key for one request instead of the server key. It is never logged or stored.

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
  -d '{"messages":[{"role":"user","content":"Hi Sarah, what problem are you facing?"}]}'
```

## Deploying on Render

The service is defined in `render.yaml`.
1. Set `SOCLAAS_API_KEY` and `SOCLAAS_MODEL` in the Render dashboard.
2. After deploying, open `https://<service>.onrender.com/health/upstream`. If it shows `"reachable": false`, Render cannot reach the SoCLaaS gateway.

Free instances sleep after about 15 minutes of inactivity. The first request after that can take around a minute.

The system prompts live in `app/prompts.py`. `PERSONA_FACTS` must stay in sync with `CASE_REVIEW_FACTS[].personaFact` in the frontend's `src/caseReview.ts`, and the ids in `COMMUNITY_ROOM_FACTS` with the facts in the frontend's `src/cases/community-room.ts`. `PERSONAS` maps each `caseId` to its persona prompt, facts and prompt version.
