"""E-008 separated generation, blind scoring, and unblinding."""

configfile: "config/experiments/E-008-blind-adfgx-replication.yaml"

PUBLIC = config["separation"]["public_suite"]
TRUTH = config["separation"]["sealed_truth"]
SCORES = config["separation"]["blind_scores"]
RESULT = config["separation"]["result"]
SCORER_CONFIG = config["separation"]["scorer_config"]


rule all:
    input:
        RESULT


rule generate_independent_suite:
    input:
        experiment="config/experiments/E-008-blind-adfgx-replication.yaml",
        manifest=config["source_manifest"],
        predecessor=config["predecessor"]["result"],
        sources=[item["path"] for item in config["parameters"]["documents"]],
    output:
        public=PUBLIC,
        truth=TRUTH,
    shell:
        "./scripts/generate-e008-blind-adfgx"


rule blind_width_search:
    input:
        public=PUBLIC,
        scorer=SCORER_CONFIG,
    output:
        SCORES
    threads: 12
    resources:
        mem_mb=8192
    shell:
        "./scripts/score-e008-blind-adfgx"


rule unblind_and_evaluate:
    input:
        public=PUBLIC,
        truth=TRUTH,
        scores=SCORES,
        experiment="config/experiments/E-008-blind-adfgx-replication.yaml",
        scorer=SCORER_CONFIG,
    output:
        RESULT
    shell:
        "./scripts/unblind-e008-adfgx"
