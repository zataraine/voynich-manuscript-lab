# Experiment index

| Run ID | Date | Hypothesis | Config | Code state | Data manifest | Device | Result | Artifact |
|---|---|---|---|---|---|---|---|---|
| E-001-manufactured-vs-hoax | 2026-08-30 | H-001 | `config/experiments/E-001-manufactured-vs-hoax.yaml` | `c1adb6a`, clean | `76db756b0cd15bbe9a65055447757ae0590690ad64dc20e2f51065cb49537ae8` | CPU, 5 workers; local GPU review | Simple nulls fail selected dimensions; copy/mutate remains compatible on 2/3 primary metrics; no posterior | `reports/E-001-preliminary.md`; raw result `b0160407…` |
| E-002-control-calibration | 2026-08-30 | H-002 | `config/experiments/E-002-control-calibration.yaml` | `7f34990`, clean | `553b0580…` Naibbe archive plus hashed IVTFF witnesses | CPU, 12 workers; Qwen and GLM GPU review | Training controls separate, but Naibbe transfer and witness stability fail; no target interpretation | `reports/E-002-control-calibration.md`; result `fea9ddd5…` |
