from pathlib import Path

import pytest

from manuscript_lab.ivtff import (
    IVTFFFormatError,
    iter_page_headers,
    iter_text_lines,
    parse_ivtff,
    parse_surface,
    summarize_page_metadata,
)


def test_page_metadata_preserves_values_and_missing_fields(tmp_path: Path) -> None:
    source = tmp_path / "sample.ivtff"
    source.write_text(
        "#=IVTFF Eva- 2.0 M 5\n"
        "<f1r> <! $L=A $H=1 $I=H>\n"
        "<f1r.1,@P0> fachys.ykal\n"
        "<f1v> <! $L=B $H=2>\n"
        "<f2r> <! $H=2>\n",
        encoding="utf-8",
    )
    headers = list(iter_page_headers(source))
    assert [header.page for header in headers] == ["f1r", "f1v", "f2r"]
    assert headers[0].fields == {"L": "A", "H": "1", "I": "H"}
    assert headers[0].raw == "<f1r> <! $L=A $H=1 $I=H>"

    report = summarize_page_metadata(source)
    assert report["page_header_count"] == 3
    assert report["currier_language_counts"] == {"<missing>": 1, "A": 1, "B": 1}
    assert report["scribal_hand_counts"] == {"1": 1, "2": 2}


def test_iter_text_lines_preserves_diplomatic_surface(tmp_path: Path) -> None:
    source = tmp_path / "fixture.ivtff"
    source.write_text(
        "#=IVTFF Eva- 2.0\n<f1r> <! $L=A $H=1 $I=H>\n<f1r.1,@P0>  <%>qokedy.[a:b]<$>\n",
        encoding="utf-8",
    )
    lines = list(iter_text_lines(source))
    assert len(lines) == 1
    assert lines[0].page == "f1r"
    assert lines[0].locator == "@P0"
    assert lines[0].text == "<%>qokedy.[a:b]<$>"
    assert lines[0].raw == "<f1r.1,@P0>  <%>qokedy.[a:b]<$>"


def test_parser_roundtrips_mixed_line_endings_and_wrapped_locus(tmp_path: Path) -> None:
    source = tmp_path / "wrapped.ivtff"
    raw = (
        b"#=IVTFF Eva- 2.0 D 9\r\n"
        b"<f1r> <! $L=A $H=1>\n"
        b"<f1r.1,@P0;Z> <%>qo.[k:t] /\r\n"
        b"/ dy,ol<!note>@221;<$>\n"
    )
    source.write_bytes(raw)

    document = parse_ivtff(source, witness_id="fixture")

    assert document.render_bytes() == raw
    assert document.header.alphabet == "Eva-"
    assert len(document.loci) == 1
    locus = document.loci[0]
    assert locus.transcriber == "Z"
    assert locus.line_numbers == (3, 4)
    assert locus.text == "<%>qo.[k:t]dy,ol<!note>@221;<$>"
    assert "alternative_reading" in {unit.kind for unit in locus.units}
    assert "uncertain_space" in {unit.kind for unit in locus.units}
    assert "free_comment" in {unit.kind for unit in locus.units}


def test_surface_parser_preserves_all_structural_text() -> None:
    surface = "<%>ab.cd,ef<->gh<~>ij{ct}[k:t:s][s:]????<!x><@L=B>@221;<$>"
    units = parse_surface(surface)

    assert "".join(unit.raw for unit in units) == surface
    assert [unit.alternatives for unit in units if unit.kind == "alternative_reading"] == [
        ("k", "t", "s"),
        ("s", ""),
    ]
    kinds = {unit.kind for unit in units}
    assert {
        "certain_space",
        "uncertain_space",
        "drawing_space",
        "misaligned_drawing_space",
        "ligature",
        "unreadable_unknown_count",
        "unreadable_character",
        "text_tag",
        "high_ascii",
    } <= kinds


def test_strict_parser_rejects_format_1_and_orphan_continuation(tmp_path: Path) -> None:
    old = tmp_path / "old.ivtff"
    old.write_text("#=IVTFF Eva- 1.5\n", encoding="ascii")
    with pytest.raises(IVTFFFormatError, match="unsupported IVTFF version"):
        parse_ivtff(old)

    broken = tmp_path / "broken.ivtff"
    broken.write_text("#=IVTFF Eva- 2.0\n/ orphan\n", encoding="ascii")
    with pytest.raises(IVTFFFormatError, match="orphan-continuation"):
        parse_ivtff(broken)
