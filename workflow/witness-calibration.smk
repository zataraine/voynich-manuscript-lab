configfile: "config/experiments/E-011-cross-fitted-witness-calibration.yaml"


rule all:
    input:
        f"{config['artifacts']['root']}/{config['artifacts']['split']}",
        f"{config['artifacts']['root']}/{config['artifacts']['calibrated_features']}",
        f"{config['artifacts']['root']}/{config['artifacts']['result']}",


rule witness_calibration:
    input:
        experiment="config/experiments/E-011-cross-fitted-witness-calibration.yaml",
        protocol=config["protocol"],
        predecessor_result=config["predecessor"]["result"],
        predecessor_features=config["predecessor"]["page_features"],
    output:
        split=f"{config['artifacts']['root']}/{config['artifacts']['split']}",
        calibrated=f"{config['artifacts']['root']}/{config['artifacts']['calibrated_features']}",
        result=f"{config['artifacts']['root']}/{config['artifacts']['result']}",
    resources:
        mem_mb=4096,
    shell:
        "./scripts/run python -m manuscript_lab.witness_calibration --config {input.experiment}"
