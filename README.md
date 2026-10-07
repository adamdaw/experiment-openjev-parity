# OpenJev–router parity experiment

On 2026-09-30, this experiment asked: does [OpenJev](https://github.com/razorback16/openjev) at commit `a938337` give the same answers as an existing Jev-compatible router when both use the same Winnow-12B llama-server, and where do their request and error handling differ? The Winnow backend at that commit is not published upstream, so the OpenJev side cannot currently be reproduced from a public commit.

## Method

The smoke runner sent requests sequentially to OpenJev (`OPENJEV_BACKEND=winnow`) and a private local baseline router using its Winnow backend. Both services shared one Winnow-12B llama-server. The generic test environment had a local Linux host with the two HTTP services and the shared inference backend; machine-specific configuration is intentionally omitted.

The request set combines:

- 15 synthetic parity fixtures copied, with approval, from the private baseline router's test data into [`data/requests.json`](data/requests.json). These cover choices, scores, boolean-like `noul` answers, unusual JSON shapes, option counts, batching, invalid input, and an overlong prompt.
- 16 generated routing cases (four synthetic prompts, each tested with two through five options).
- two generated 64-option ownership cases.
- one generated JevBench-like customer-support case. This is a locally constructed shape only; no hosted benchmark results are used.

For responses where both services returned HTTP 200, the runner compared the top answer for every question and tracked the largest absolute probability difference. It also recorded status-code differences. The generator definitions are included directly in [`smoke.py`](smoke.py).

## Results

The recorded run is in [`results/smoke-2026-09-30.txt`](results/smoke-2026-09-30.txt). Its summary is:

> questions compared: 98; same top answer: 98; largest probability gap: 0.0106

The error-handling differences were:

- The multi-question fixture was rejected by OpenJev with 422 while the baseline accepted it with 200.
- The overlong prompt returned 400 from OpenJev and 422 from the baseline.
- OpenJev handled both generated 64-option cases with 200; the baseline returned 500 for both.

These statements correspond to lines 6, 14, 32–33, and 36 of the committed output.

## Limitations

This was one sequential run with 98 jointly successful questions, not a statistical evaluation. The baseline router is private, so others cannot reproduce that side exactly; use the runner against your own Jev-compatible baseline. Timing was recorded incidentally but was not the study question.

A separate week of real-traffic observation is excluded. It was inconclusive because too few requests reached OpenJev and the two systems' latency definitions are not comparable. No traffic data or traffic-logging/summarization tooling is included here.

## Reproduce

Requires Python 3 and two already-running Jev-compatible HTTP services. The runner does not start or configure services.

```sh
python smoke.py --check-fixtures
python smoke.py \
  --openjev-url http://localhost:8000 \
  --baseline-url http://localhost:8001 \
  --fixtures data/requests.json
```

The same settings may be supplied through `OPENJEV_URL`, `BASELINE_URL`, and `PARITY_FIXTURES`; `PARITY_RESULTS` selects the recorded output used by the offline check. Run `python smoke.py --help` for details. Service behavior can vary with model/server versions and configuration.

## License

No license has been selected. That remains an open project-owner decision.
