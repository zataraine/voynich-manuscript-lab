"""E-009 separated ciphertext generation, scoring, and unblinding."""

configfile: "config/experiments/E-009-ciphertext-only-structure.yaml"

PUBLIC = config["separation"]["public_suite"]
TRUTH = config["separation"]["sealed_truth"]
SCORES = config["separation"]["blind_scores"]
RESULT = config["separation"]["result"]
SCORER_CONFIG = config["separation"]["scorer_config"]


rule all:
    input:
        RESULT


rule generate_ciphertext_only_controls:
    input:
        experiment="config/experiments/E-009-ciphertext-only-structure.yaml",
        manifest=config["source_manifest"],
        predecessor=config["predecessor"]["result"],
        sources=[item["path"] for item in config["parameters"]["documents"]],
    output:
        public=PUBLIC,
        truth=TRUTH,
    shell:
        "./scripts/generate-e009-ciphertext-only"


rule blind_intrinsic_search:
    input:
        public=PUBLIC,
        scorer=SCORER_CONFIG,
    output:
        SCORES
    threads: 12
    resources:
        mem_mb=8192
    shell:
        "./scripts/score-e009-ciphertext-only"


rule unblind_ciphertext_structure:
    input:
        public=PUBLIC,
        truth=TRUTH,
        scores=SCORES,
        experiment="config/experiments/E-009-ciphertext-only-structure.yaml",
        scorer=SCORER_CONFIG,
    output:
        RESULT
    shell:
        "./scripts/unblind-e009-ciphertext-only"
