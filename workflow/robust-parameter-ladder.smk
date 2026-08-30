"""E-004 parameter-distribution robustness campaign."""

configfile: "config/experiments/E-004-robust-parameter-ladder.yaml"

RUN_ROOT = config["artifacts"]["root"]
RESULT = f"{RUN_ROOT}/result.json"
PACKET = f"{RUN_ROOT}/reference-packet.json"
QWEN = f"{RUN_ROOT}/qwen-review.json"
CRITIC = f"{RUN_ROOT}/glm-critic.json"


rule all:
    input:
        QWEN,
        CRITIC


rule deterministic_robust_parameter_ladder:
    input:
        archive=config["parameters"]["control_archive"],
        manifest=config["source_manifest"],
        experiment="config/experiments/E-004-robust-parameter-ladder.yaml",
    output:
        RESULT
    threads: 12
    resources:
        mem_mb=65536
    shell:
        "./scripts/run python -m manuscript_lab.robust_parameter_ladder "
        "--config {input.experiment} --output {output}"


rule retrieve_methodological_context:
    input:
        result=RESULT,
        experiment="config/experiments/E-004-robust-parameter-ladder.yaml",
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
        system_prompt="config/prompts/routine-review-system-v1.txt",
        user_prompt="config/prompts/routine-review-user-v1.txt",
    output:
        QWEN
    resources:
        local_ai=1,
        gpu=1
    shell:
        "./scripts/run python -m manuscript_lab.robust_ladder_review qwen "
        "--result {input.result} --packet {input.packet} --output {output}"


rule glm_critic:
    input:
        result=RESULT,
        packet=PACKET,
        modelfile="config/models/glm-critic-v1.Modelfile",
        system_prompt="config/prompts/adversarial-critic-system-v1.txt",
        user_prompt="config/prompts/adversarial-critic-user-v1.txt",
    output:
        CRITIC
    resources:
        local_ai=1,
        gpu=1
    shell:
        "./scripts/run python -m manuscript_lab.robust_ladder_review critic "
        "--result {input.result} --packet {input.packet} --output {output}"
