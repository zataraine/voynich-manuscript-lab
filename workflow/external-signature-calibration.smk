configfile: "config/experiments/E-013-external-signature-calibration.yaml"


rule all:
    input:
        config["artifacts"]["case_features"],
        config["artifacts"]["model"],
        config["artifacts"]["result"],


rule external_signature_calibration:
    input:
        experiment="config/experiments/E-013-external-signature-calibration.yaml",
        protocol=config["protocol"],
        predecessor=config["predecessor"]["result"],
        development=config["sources"]["development_manifest"],
        independent=[item["path"] for item in config["sources"]["independent_manifests"]],
        external_manifest=config["sources"]["external_manifest"],
        external_archive=config["sources"]["external_archive"],
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
