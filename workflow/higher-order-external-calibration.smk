configfile: "config/experiments/E-014-higher-order-external-calibration.yaml"


rule all:
    input:
        config["artifacts"]["case_features"],
        config["artifacts"]["model"],
        config["artifacts"]["result"],


rule higher_order_external_calibration:
    input:
        experiment="config/experiments/E-014-higher-order-external-calibration.yaml",
        predecessor=config["predecessor"]["result"],
        implementation="src/manuscript_lab/higher_order_calibration.py",
    output:
        features=config["artifacts"]["case_features"],
        model=config["artifacts"]["model"],
        result=config["artifacts"]["result"],
    threads: 12
    resources:
        mem_mb=16384,
    shell:
        "./scripts/run python -m manuscript_lab.higher_order_calibration "
        "--config {input.experiment}"
