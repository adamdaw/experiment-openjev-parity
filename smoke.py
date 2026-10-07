"""Smoke-compare OpenJev with a Jev-compatible baseline service."""

import argparse
import json
import os
import re
import string
import time
import urllib.error
import urllib.request
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--openjev-url",
        default=os.environ.get("OPENJEV_URL", "http://localhost:8000"),
        help="OpenJev base URL (env: OPENJEV_URL; default: %(default)s)",
    )
    parser.add_argument(
        "--baseline-url",
        default=os.environ.get("BASELINE_URL", "http://localhost:8001"),
        help="baseline service base URL (env: BASELINE_URL; default: %(default)s)",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path(os.environ.get("PARITY_FIXTURES", "data/requests.json")),
        help="parity fixture JSON (env: PARITY_FIXTURES; default: %(default)s)",
    )
    parser.add_argument(
        "--check-fixtures",
        action="store_true",
        help="load cases and report counts without calling either service",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path(os.environ.get("PARITY_RESULTS", "results/smoke-2026-09-30.txt")),
        help="recorded output used by --check-fixtures (env: PARITY_RESULTS; default: %(default)s)",
    )
    return parser.parse_args()


def post(base_url, body):
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/systemone",
        json.dumps(body).encode(),
        {"content-type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return response.status, json.load(response), time.perf_counter() - started
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}"), time.perf_counter() - started


def top(answer):
    answer_type = answer.get("type")
    if answer_type == "choice":
        return answer["choice"]
    if answer_type == "score":
        probabilities = answer["probabilities"]
        return "L" + max(probabilities, key=probabilities.get)
    if answer_type == "noul":
        return answer["noul"] >= 0.5
    return None


def probs(answer):
    if answer.get("type") == "noul":
        return {"true": answer["noul"]}
    return answer.get("probabilities") or {}


def load_cases(fixtures):
    with fixtures.open(encoding="utf-8") as fixture_file:
        requests = [
            ("parity/" + item["name"], item["body"])
            for item in json.load(fixture_file)
        ]

    route_states = [
        "User: rename a variable across three files in this TypeScript repo.",
        "User: design a distributed consensus protocol and prove its safety.",
        "User: what's the weather like? (no tools available)",
        "User: summarise this 400-line log and find the root cause of the crash.",
    ]
    tiers = {
        "haiku": "fast, cheap, simple edits",
        "sonnet": "solid general coding",
        "opus": "hardest reasoning",
        "local": "on-device model, private and free",
        "mac-openjev": "Mac-hosted router",
    }
    for index, state in enumerate(route_states):
        for option_count in (2, 3, 4, 5):
            keys = list(tiers)[:option_count]
            requests.append(
                (
                    f"route/{index}/{option_count}opt",
                    {
                        "model": "winnow-12b",
                        "state": state,
                        "questions": {
                            "tier": {
                                "type": "choice",
                                "instructions": "Which option should handle this request?",
                                "criteria": {key: tiers[key] for key in keys},
                            },
                            "needs_tools": {
                                "type": "noul",
                                "instructions": "Does this need tool use?",
                            },
                            "difficulty": {
                                "type": "score",
                                "instructions": "How difficult is this?",
                                "criteria": ["easy", "medium", "hard"],
                            },
                        },
                    },
                )
            )

    labels = [f"opt_{letter}{number}" for letter in string.ascii_lowercase[:8] for number in range(8)]
    topics = ["billing", "networking", "UI bugs", "databases", "auth", "docs", "performance", "security"]
    criteria_64 = {
        key: f"Handles topic number {index}: {topics[index % 8]} (area {index // 8})"
        for index, key in enumerate(labels)
    }
    requests.append(
        (
            "64opt/db",
            {
                "model": "winnow-12b",
                "state": "The Postgres primary in area 3 is refusing connections after a failover.",
                "questions": {
                    "owner": {
                        "type": "choice",
                        "instructions": "Which team owns this issue?",
                        "criteria": criteria_64,
                    }
                },
            },
        )
    )
    requests.append(
        (
            "64opt/auth",
            {
                "model": "winnow-12b",
                "state": "Users in area 5 cannot log in; SSO tokens are rejected as expired.",
                "questions": {
                    "owner": {
                        "type": "choice",
                        "instructions": "Which team owns this issue?",
                        "criteria": criteria_64,
                    }
                },
            },
        )
    )
    requests.append(
        (
            "jevbench-like",
            {
                "model": "winnow-12b",
                "state": {
                    "conversation": [
                        {"role": "user", "content": "I ordered the blue jacket in size M but got a red one in L. Order #4471."},
                        {"role": "agent", "content": "Sorry about that! Would you like a replacement or a refund?"},
                        {"role": "user", "content": "Replacement please, and I need it before Friday."},
                    ],
                    "policy": {"free_expedited_on_error": True, "max_days": 5},
                },
                "questions": {
                    "intent": {
                        "type": "choice",
                        "instructions": "What does the customer want now?",
                        "criteria": {
                            "refund": "Money back",
                            "replacement": "The correct item sent",
                            "cancel": "Cancel the order",
                            "info": "Just information",
                        },
                    },
                    "expedite": {
                        "type": "noul",
                        "instructions": "Should shipping be expedited under the policy?",
                    },
                    "sentiment": {
                        "type": "score",
                        "instructions": "How upset is the customer?",
                        "criteria": ["calm", "mildly annoyed", "upset", "furious"],
                    },
                },
            },
        )
    )
    return requests


def check_fixtures(requests, results):
    parity = [body for name, body in requests if name.startswith("parity/")]
    generated = len(requests) - len(parity)
    parity_questions = sum(len(body.get("questions", {})) for body in parity)
    all_questions = sum(len(body.get("questions", {})) for _, body in requests)
    print(f"fixture cases: {len(parity)}; generated cases: {generated}; total cases: {len(requests)}")
    print(f"fixture questions: {parity_questions}; all submitted questions: {all_questions}")
    summary = re.search(
        r"^questions compared: (\d+);",
        results.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not summary:
        raise ValueError(f"question count not found in {results}")
    print(f"recorded jointly successful questions: {summary.group(1)} (from {results})")


def run(requests, openjev_url, baseline_url):
    same = total = 0
    worst = 0.0
    for name, body in requests:
        body = dict(body, model="winnow-12b")
        openjev_status, openjev_response, openjev_time = post(openjev_url, body)
        baseline_status, baseline_response, baseline_time = post(baseline_url, body)
        line = (
            f"{name:28s} openjev {openjev_status} {openjev_time:5.2f}s | "
            f"router {baseline_status} {baseline_time:5.2f}s"
        )
        if openjev_status == 200 and baseline_status == 200:
            differences = []
            for question, baseline_answer in baseline_response["answers"].items():
                openjev_answer = openjev_response["answers"].get(question, {})
                total += 1
                if top(openjev_answer) == top(baseline_answer):
                    same += 1
                else:
                    differences.append(
                        f"{question}: {top(openjev_answer)} vs {top(baseline_answer)}"
                    )
                openjev_probs = probs(openjev_answer)
                baseline_probs = probs(baseline_answer)
                gap = max(
                    (abs(openjev_probs.get(key, 0) - value) for key, value in baseline_probs.items()),
                    default=0,
                )
                worst = max(worst, gap)
            line += f" | top-answer diffs: {differences or 'none'}"
        print(line, flush=True)
    print(
        f"\nquestions compared: {total}; same top answer: {same}; "
        f"largest probability gap: {worst:.4f}"
    )


def main():
    args = parse_args()
    requests = load_cases(args.fixtures)
    if args.check_fixtures:
        check_fixtures(requests, args.results)
        return
    run(requests, args.openjev_url, args.baseline_url)


if __name__ == "__main__":
    main()
