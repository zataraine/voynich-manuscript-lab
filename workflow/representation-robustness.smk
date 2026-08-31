configfile: "config/experiments/E-010-representation-robustness.yaml"


rule all:
    input:
        f"{config['artifacts']['root']}/{config['artifacts']['page_features']}",
        f"{config['artifacts']['root']}/{config['artifacts']['result']}",


rule representation_robustness:
    input:
        experiment="config/experiments/E-010-representation-robustness.yaml",
        protocol=config["protocol"],
        registry=config["source_registry"],
        lattice=config["source_lattice"],
    output:
        page_features=f"{config['artifacts']['root']}/{config['artifacts']['page_features']}",
        result=f"{config['artifacts']['root']}/{config['artifacts']['result']}",
    resources:
        mem_mb=8192,
    shell:
        "./scripts/run python -m manuscript_lab.representation_robustness "
        "--config {input.experiment}"
