# OpenJev–router parity experiment

On 2026-09-30, this experiment asked: does OpenJev (upstream: [razorback16/openjev](https://github.com/razorback16/openjev)), with the Winnow backend from Adam Daw's fork at commit [`a938337`](https://github.com/adamdaw/openjev/tree/a938337deda63bb5b97a24003d16b69d7e62d4e8) (branch `winnow-backend`, not merged upstream), give the same answers as an existing Jev-compatible router when both use the same Winnow-12B llama-server, and where do their request and error handling differ?

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

To run the OpenJev side, check out the commit that was tested and start it with the Winnow backend. It expects a llama-server serving Winnow-12B at `OPENJEV_UPSTREAM` (default `http://127.0.0.1:8000`); the fork's README ("Winnow" section) documents how to set that up.

```sh
git clone https://github.com/adamdaw/openjev.git
git -C openjev checkout a938337deda63bb5b97a24003d16b69d7e62d4e8
pip install -e ./openjev
OPENJEV_BACKEND=winnow python -m openjev
```

OpenJev's API listens on `http://127.0.0.1:8080` by default. For the baseline, use your own Jev-compatible router (see Limitations). Then run the comparison:

```sh
python smoke.py --check-fixtures
python smoke.py \
  --openjev-url http://127.0.0.1:8080 \
  --baseline-url http://localhost:8001 \
  --fixtures data/requests.json
```

The same settings may be supplied through `OPENJEV_URL`, `BASELINE_URL`, and `PARITY_FIXTURES`; `PARITY_RESULTS` selects the recorded output used by the offline check. Run `python smoke.py --help` for details. Service behavior can vary with model/server versions and configuration.

## License

- Code (`smoke.py`) is under the MIT License; see [`LICENSE`](LICENSE).
- **Data and prose: CC BY 4.0** ([`LICENSE-CC-BY-4.0.txt`](LICENSE-CC-BY-4.0.txt)). Applies only to original content by Adam Daw (© 2026) in `README.md`, `data/` and `results/`. It does not apply to third-party material in those paths, including model-generated answers and probabilities in `results/`; that material keeps its own terms.

The model outputs in `results/` are included so the results can be checked.

OpenJev (Apache-2.0) and the Winnow-12B model (Apache-2.0, per its model card) keep their own terms. Neither is redistributed here.
