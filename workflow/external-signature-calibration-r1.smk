configfile: "config/experiments/E-013R1-external-signature-calibration.yaml"


rule all:
    input:
        config["artifacts"]["case_features"],
        config["artifacts"]["model"],
        config["artifacts"]["result"],


rule external_signature_calibration_r1:
    input:
        experiment="config/experiments/E-013R1-external-signature-calibration.yaml",
        base=config["base_config"],
        predecessor=config["predecessor_attempt"]["result"],
        implementation="src/manuscript_lab/external_signature_calibration.py",
    output:
        features=config["artifacts"]["case_features"],
        model=config["artifacts"]["model"],
        result=config["artifacts"]["result"],
    threads: 12
    resources:
        mem_mb=16384,
    shell:
        "./scripts/run python -m manuscript_lab.external_signature_calibration "
        "--config {input.experiment}"
