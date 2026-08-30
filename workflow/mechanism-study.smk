"""Long, resumable first mechanism study with bounded local-AI supervision."""


configfile: "config/experiments/E-001-manufactured-vs-hoax.yaml"

RUN_ROOT = config["artifacts"]["root"]
RESULT = f"{RUN_ROOT}/result.json"
PACKET = f"{RUN_ROOT}/reference-packet.json"
REVIEW = f"{RUN_ROOT}/qwen-review.json"


rule all:
    input:
        REVIEW


rule deterministic_mechanism_panel:
    input:
        source=config["parameters"]["input_path"],
        manifest=config["source_manifest"],
        experiment="config/experiments/E-001-manufactured-vs-hoax.yaml",
    output:
        RESULT
    threads: 12
    resources:
        mem_mb=16384
    shell:
        "./scripts/run python -m manuscript_lab.mechanism_test "
        "--config {input.experiment} --output {output}"


rule retrieve_methodological_context:
    input:
        result=RESULT,
        experiment="config/experiments/E-001-manufactured-vs-hoax.yaml",
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
        REVIEW
    resources:
        local_ai=1,
        gpu=1
    shell:
        "./scripts/run python -m manuscript_lab.study_review review "
        "--result {input.result} --packet {input.packet} --output {output}"
