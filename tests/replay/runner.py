"""Persona replay suite (WP4): plays each script against the live structured client and reports, per
fact, how often the client disclosed it when it shouldn't (false positive) or didn't when it should
(false negative). Calls the real model, so it runs on demand, never in the normal test run:

    .venv/Scripts/python -m tests.replay.runner --runs 3 --out replay-report.json

Reads the model settings from the environment, or from .env in the working directory.
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from app.client import structured_reply
from app.prompts import CASE_FACTS, PERSONAS

SCRIPTS_DIR = Path(__file__).parent
OPENING = {
    # The client's first message in each case (src/cases/<case>.ts openingMessage).
    "community-room": "Hi, I'm Mei — I run the front desk here at Bukit Cahaya Community Centre. Our room bookings have become a bit of a headache. Ask me anything!",
}
TARGETS = {"falsePositiveRate": 0.05, "falseNegativeRate": 0.10}
# SoCLaaS rate-limits bursts, so a failed script run waits and is retried from the start.
BACKOFF_SECONDS = [10, 20, 40, 60, 90]
RETRIES = len(BACKOFF_SECONDS) + 1


def load_scripts(case_id: str) -> list[dict]:
    data = json.loads((SCRIPTS_DIR / f"{case_id}.replay.json").read_text(encoding="utf-8"))
    assert data["caseId"] == case_id
    return data["scripts"]


async def play(llm, slots, case_id: str, script: dict) -> dict:
    """One run of one script: the engineer messages in order, with live client replies."""
    history = [{"role": "assistant", "content": OPENING[case_id]}]
    disclosed: set[str] = set()
    turns = []
    for text in script["messages"]:
        history.append({"role": "user", "content": text})
        result = await structured_reply(llm, slots, case_id, history)
        history.append({"role": "assistant", "content": result["reply"], "disclosedFactIds": result["disclosedFactIds"]})
        disclosed |= set(result["disclosedFactIds"])
        turns.append({"engineer": text, "reply": result["reply"], "disclosedFactIds": result["disclosedFactIds"], "guard": result["guard"]})
    return {
        "disclosed": sorted(disclosed),
        "falsePositives": sorted(disclosed & set(script["mustNotDisclose"])),
        "falseNegatives": sorted(set(script["mustDisclose"]) - disclosed),
        "turns": turns,
    }


def summarise(case_id: str, results: list[dict]) -> dict:
    """Per-fact and overall rates. A fact's FP rate is over the runs that forbid it; FN over those that need it."""
    per_fact = {}
    totals = {"fp": 0, "fp_n": 0, "fn": 0, "fn_n": 0}
    for fact in CASE_FACTS[case_id]:
        fact_id = fact["id"]
        forbidden = [r for r in results if fact_id in r["script"]["mustNotDisclose"]]
        required = [r for r in results if fact_id in r["script"]["mustDisclose"]]
        fp = sum(fact_id in r["run"]["falsePositives"] for r in forbidden)
        fn = sum(fact_id in r["run"]["falseNegatives"] for r in required)
        totals["fp"] += fp
        totals["fp_n"] += len(forbidden)
        totals["fn"] += fn
        totals["fn_n"] += len(required)
        per_fact[fact_id] = {
            "falsePositives": fp,
            "forbiddenRuns": len(forbidden),
            "falsePositiveRate": round(fp / len(forbidden), 3) if forbidden else None,
            "falseNegatives": fn,
            "requiredRuns": len(required),
            "falseNegativeRate": round(fn / len(required), 3) if required else None,
        }
    fp_rate = totals["fp"] / totals["fp_n"] if totals["fp_n"] else 0.0
    fn_rate = totals["fn"] / totals["fn_n"] if totals["fn_n"] else 0.0
    failing = [
        fact_id
        for fact_id, row in per_fact.items()
        if (row["falsePositiveRate"] or 0) > TARGETS["falsePositiveRate"]
        or (row["falseNegativeRate"] or 0) > TARGETS["falseNegativeRate"]
    ]
    return {
        "falsePositiveRate": round(fp_rate, 3),
        "falseNegativeRate": round(fn_rate, 3),
        "meetsTargets": fp_rate <= TARGETS["falsePositiveRate"] and fn_rate <= TARGETS["falseNegativeRate"],
        "failingFacts": failing,
        "perFact": per_fact,
        "guardActions": {
            action: sum(turn["guard"]["action"] == action for r in results for turn in r["run"]["turns"])
            for action in ("ok", "regenerated", "guard_block")
        },
    }


async def run_suite(case_ids: list[str], runs: int, concurrency: int) -> dict:
    from app.config import Settings
    from app.llm import LLM, UpstreamSlots, create_client

    settings = Settings.from_env()
    llm = LLM(create_client(settings), settings.soclaas_model)
    slots = UpstreamSlots(concurrency)
    gate = asyncio.Semaphore(concurrency)

    async def one(case_id: str, script: dict, run: int) -> dict:
        async with gate:
            for attempt in range(RETRIES):
                try:
                    return {"case": case_id, "script": script, "runIndex": run, "run": await play(llm, slots, case_id, script)}
                except Exception as error:  # rate limits and other upstream hiccups: retry the whole script run
                    if attempt == RETRIES - 1:
                        return {"case": case_id, "script": script, "runIndex": run, "error": f"{type(error).__name__}: {error}"}
                    retry_after = (getattr(error, "headers", None) or {}).get("Retry-After")
                    await asyncio.sleep(float(retry_after) if retry_after else BACKOFF_SECONDS[attempt])

    jobs = [one(case_id, script, run) for case_id in case_ids for script in load_scripts(case_id) for run in range(runs)]
    started = time.time()
    done = await asyncio.gather(*jobs)
    report = {
        "model": settings.soclaas_model,
        "temperature": 1,
        "runsPerScript": runs,
        "targets": TARGETS,
        "seconds": round(time.time() - started),
        "cases": {},
    }
    for case_id in case_ids:
        results = [item for item in done if item["case"] == case_id and "run" in item]
        errors = [item for item in done if item["case"] == case_id and "error" in item]
        report["cases"][case_id] = {
            **summarise(case_id, results),
            "scripts": len(load_scripts(case_id)),
            "errors": [{"script": item["script"]["id"], "error": item["error"]} for item in errors],
            "misses": [
                {
                    "script": item["script"]["id"],
                    "run": item["runIndex"],
                    "falsePositives": item["run"]["falsePositives"],
                    "falseNegatives": item["run"]["falseNegatives"],
                    "turns": item["run"]["turns"],
                }
                for item in results
                if item["run"]["falsePositives"] or item["run"]["falseNegatives"]
            ],
        }
    return report


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", action="append", choices=sorted(PERSONAS), help="Case to replay (default: all)")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--out", type=Path, default=Path("replay-report.json"))
    args = parser.parse_args()
    load_dotenv(Path(".env"))
    report = asyncio.run(run_suite(args.case or sorted(PERSONAS), args.runs, args.concurrency))
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for case_id, case in report["cases"].items():
        print(
            f"{case_id}: FP {case['falsePositiveRate']:.1%}, FN {case['falseNegativeRate']:.1%}, "
            f"meets targets: {case['meetsTargets']}, failing facts: {case['failingFacts']}, errors: {len(case['errors'])}"
        )
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
