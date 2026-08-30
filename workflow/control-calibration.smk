"""Resumable control-calibration campaign with two bounded local reviewers."""

configfile: "config/experiments/E-002-control-calibration.yaml"

RUN_ROOT = config["artifacts"]["root"]
RESULT = f"{RUN_ROOT}/result.json"
PACKET = f"{RUN_ROOT}/reference-packet.json"
QWEN = f"{RUN_ROOT}/qwen-review.json"
CRITIC = f"{RUN_ROOT}/glm-critic.json"


rule all:
    input:
        QWEN,
        CRITIC


rule deterministic_control_calibration:
    input:
        archive=config["parameters"]["control_archive"],
        manifest=config["source_manifest"],
        experiment="config/experiments/E-002-control-calibration.yaml",
        witnesses=list(config["parameters"]["voynich_witnesses"].values()),
    output:
        RESULT
    threads: 12
    resources:
        mem_mb=16384
    shell:
        "./scripts/run python -m manuscript_lab.control_calibration "
        "--config {input.experiment} --output {output}"


rule retrieve_methodological_context:
    input:
        result=RESULT,
        experiment="config/experiments/E-002-control-calibration.yaml",
        references=config["parameters"]["local_ai"]["reference_documents"],
    output:
        PACKET
    resources:
        local_ai=1,
        gpu=1
    shell:
        "./scripts/run python -m manuscript_lab.study_review packet "
        "--config {input.experiment} --output {output}"


rule qwen_review:
    input:
        result=RESULT,
        packet=PACKET,
    output:
        QWEN
    resources:
        local_ai=1,
        gpu=1
    shell:
        "./scripts/run python -m manuscript_lab.calibration_review qwen "
        "--result {input.result} --packet {input.packet} --output {output}"


rule glm_critic:
    input:
        result=RESULT,
        packet=PACKET,
    output:
        CRITIC
    resources:
        local_ai=1,
        gpu=1
    shell:
        "./scripts/run python -m manuscript_lab.calibration_review critic "
        "--result {input.result} --packet {input.packet} --output {output}"
