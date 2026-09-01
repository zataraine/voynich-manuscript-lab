configfile: "config/experiments/E-012-multi-witness-mechanism-replication.yaml"


rule all:
    input:
        f"{config['artifacts']['root']}/{config['artifacts']['symbol_map']}",
        f"{config['artifacts']['root']}/{config['artifacts']['split']}",
        f"{config['artifacts']['root']}/{config['artifacts']['result']}",


rule multi_witness_replication:
    input:
        experiment="config/experiments/E-012-multi-witness-mechanism-replication.yaml",
        protocol=config["protocol"],
        registry=config["witness_registry"],
        lattice=config["source_lattice"],
        e001=config["predecessors"]["e001_result"],
        e010=config["predecessors"]["e010_result"],
        e011=config["predecessors"]["e011_result"],
    output:
        symbol_map=f"{config['artifacts']['root']}/{config['artifacts']['symbol_map']}",
        split=f"{config['artifacts']['root']}/{config['artifacts']['split']}",
        result=f"{config['artifacts']['root']}/{config['artifacts']['result']}",
    threads: 12
    resources:
        mem_mb=16384,
    shell:
        "./scripts/run python -m manuscript_lab.multi_witness_replication "
        "--config {input.experiment}"
