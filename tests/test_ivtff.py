from pathlib import Path

from manuscript_lab.ivtff import iter_page_headers, summarize_page_metadata


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
