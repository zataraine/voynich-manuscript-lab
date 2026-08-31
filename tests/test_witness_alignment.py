from pathlib import Path

import yaml

from manuscript_lab.witness_alignment import (
    build_alignment,
    load_witness_corpus,
    sta_tokens,
    write_alignment,
)


def _write_witness(path: Path, body: str, alphabet: str = "Eva-") -> None:
    path.write_text(f"#=IVTFF {alphabet} 2.0 M 1\n" + body, encoding="ascii")


def test_alignment_preserves_missingness_lineage_and_surfaces(tmp_path: Path) -> None:
    _write_witness(
        tmp_path / "a.txt",
        "<f1r> <! $L=A>\n<f1r.1,@P0> abc\n<f1r.2,+P0> def\n",
    )
    _write_witness(
        tmp_path / "b.txt",
        "<f1r> <! $L=A>\n<f1r.1,@P0> <%>abc\n<f1r.3,+P0> ghi\n",
    )
    _write_witness(
        tmp_path / "c.txt",
        "<f1r> <! $L=A>\n<f1r.1,@P0> xyz\n<f2r> <! $L=A>\n<f2r.1,@P0> jkl\n",
        alphabet="FSG-",
    )
    _write_witness(
        tmp_path / "a-sta.txt",
        "<f1r> <! $L=A>\n<f1r.1,@P0> A1\n<f1r.2,+P0> B1\n",
        alphabet="STA1",
    )
    _write_witness(
        tmp_path / "b-sta.txt",
        "<f1r> <! $L=A>\n<f1r.1,@P0> <%>A1\n<f1r.3,+P0> C1\n",
        alphabet="STA1",
    )
    source_manifest = tmp_path / "source.yaml"
    source_manifest.write_text("schema_version: '1.0'\n", encoding="utf-8")
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "order_witness": "A",
                "source_manifest": source_manifest.as_posix(),
                "witnesses": [
                    {
                        "id": "A",
                        "path": (tmp_path / "a.txt").as_posix(),
                        "alphabet": "Eva-",
                        "lineage_group": "one",
                        "comparison_group": "eva",
                        "comparison_path": (tmp_path / "a-sta.txt").as_posix(),
                        "comparison_alternates": [],
                        "independence_role": "primary",
                        "derived_from": [],
                    },
                    {
                        "id": "B",
                        "path": (tmp_path / "b.txt").as_posix(),
                        "alphabet": "Eva-",
                        "lineage_group": "one",
                        "comparison_group": "eva",
                        "comparison_path": (tmp_path / "b-sta.txt").as_posix(),
                        "comparison_alternates": [],
                        "independence_role": "related-derivative",
                        "derived_from": ["A"],
                    },
                    {
                        "id": "C",
                        "path": (tmp_path / "c.txt").as_posix(),
                        "alphabet": "FSG-",
                        "lineage_group": "two",
                        "comparison_group": None,
                        "comparison_path": None,
                        "comparison_alternates": [],
                        "independence_role": "primary",
                        "derived_from": [],
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = build_alignment(load_witness_corpus(registry))

    assert [cell["locus_key"] for cell in result.cells] == [
        "f1r.1",
        "f1r.2",
        "f1r.3",
        "f2r.1",
    ]
    assert result.audit["input_reading_count"] == 6
    assert result.audit["output_reading_count"] == 6
    assert result.audit["unique_reading_record_count"] == 6
    first = result.cells[0]
    assert first["comparisons"]["eva"]["status"] == "markup-only-difference"
    assert [reading["diplomatic_surface"] for reading in first["readings"]] == [
        "abc",
        "<%>abc",
        "xyz",
    ]
    assert first["readings"][0]["reading_surface"] == "abc"
    assert first["readings"][1]["reading_surface"] == "abc"
    assert first["readings"][0]["comparison_view"]["reading_surface"] == "A1"
    assert first["comparisons"]["eva"]["pairs"]["A::B"] == {
        "status": "same",
        "sta1_token_similarity": 1.0,
    }
    comparison_locus = load_witness_corpus(registry).comparison_documents["A"].loci[0]
    assert sta_tokens(comparison_locus) == ("A1",)
    assert result.cells[-1]["coverage"] == {
        "A": "page-not-covered",
        "B": "page-not-covered",
        "C": "present",
    }

    output = tmp_path / "lattice.jsonl"
    audit = tmp_path / "audit.json"
    write_alignment(result, output, audit)
    assert len(output.read_text(encoding="utf-8").splitlines()) == 5
    assert audit.is_file()
