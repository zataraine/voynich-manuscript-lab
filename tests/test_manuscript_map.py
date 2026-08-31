import json
from pathlib import Path

from manuscript_lab.ivtff import parse_ivtff
from manuscript_lab.manuscript_map import (
    link_loci_to_canvases,
    load_iiif_canvases,
    mapping_audit,
    physical_folios_for_ivtff_page,
)


def _canvas(canvas_id: str, label: str) -> dict:
    return {
        "id": f"https://example.invalid/canvas/{canvas_id}",
        "type": "Canvas",
        "label": {"none": [label]},
        "width": 1000,
        "height": 2000,
        "items": [
            {
                "type": "AnnotationPage",
                "items": [
                    {
                        "type": "Annotation",
                        "body": {
                            "id": f"https://example.invalid/image/{canvas_id}.jpg",
                            "service": [{"id": f"https://example.invalid/iiif/{canvas_id}"}],
                        },
                    }
                ],
            }
        ],
    }


def test_foldout_mapping_is_explicitly_many_to_many(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "items": [
                    _canvas("a", "69v and 70r"),
                    _canvas("b", "70v (part)"),
                    _canvas("c", "70v (part)"),
                    _canvas("d", "85v and 86r (foldout)"),
                ]
            }
        ),
        encoding="utf-8",
    )
    witness_path = tmp_path / "witness.ivtff"
    witness_path.write_text(
        "#=IVTFF Eva- 2.0 M 5\n"
        "<f70r1> <! $L=B>\n"
        "<f70r1.1,@P0> abc\n"
        "<f70v2> <! $L=B>\n"
        "<f70v2.1,@P0> def\n"
        "<fRos> <! $L=B>\n"
        "<fRos.1,@P0> ghi\n",
        encoding="ascii",
    )

    document = parse_ivtff(witness_path, witness_id="W")
    canvases = load_iiif_canvases(manifest_path)
    links = link_loci_to_canvases(document, canvases)

    assert physical_folios_for_ivtff_page("f70r1") == ("f70r",)
    assert physical_folios_for_ivtff_page("fRos") == ("f85v", "f86r")
    by_page = {}
    for link in links:
        by_page.setdefault(link.ivtff_page, []).append(link.canvas_label)
    assert by_page == {
        "f70r1": ["69v and 70r"],
        "f70v2": ["70v (part)", "70v (part)"],
        "fRos": ["85v and 86r (foldout)"],
    }
    audit = mapping_audit(document, canvases, manifest_path)
    assert audit["linked_locus_count"] == 3
    assert audit["multi_canvas_locus_count"] == 1
    assert audit["unlinked_locus_ids"] == []
