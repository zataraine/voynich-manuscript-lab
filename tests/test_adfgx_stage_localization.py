from __future__ import annotations

import itertools

import numpy as np

from manuscript_lab.adfgx_stage_localization import (
    _encode_coordinates,
    _encode_plain,
    _permutations,
    _restore_columns,
    _score_one,
    adfgx_encipher,
    best_combined_scores,
    columnar_decipher,
    columnar_encipher,
    defractionate,
    fractionate,
    keyword_read_order,
    modal_consistency_score,
    tie_safe_retrieval,
)


def test_cryptii_cargo_known_vector() -> None:
    square = "BTALPDHOZKQFVSNGICUXMREWY"
    intermediate, ciphertext = adfgx_encipher("ATTACKATONCE", square, "CARGO")
    assert ciphertext == "FAXDFADDDGDGFFFAFAXAFAFX"
    assert defractionate(intermediate, square) == "ATTACKATONCE"


def test_columnar_roundtrip_including_ragged_columns() -> None:
    stream = "ADFGX" * 13
    order = keyword_read_order("NETWORK")
    ciphertext = columnar_encipher(stream, order)
    assert columnar_decipher(ciphertext, order) == stream


def test_compiled_score_matches_reference_and_restoration() -> None:
    square = "LABYRINTHCDEFGKMOPQSUVWXZ"
    plain_text = "THEQUICKBROWNFOXIUMPSOVERTHELAZYDOG".replace("J", "I")
    stream = fractionate(plain_text, square)
    plain = _encode_plain(plain_text)
    coordinates = _encode_coordinates(stream)
    assert _score_one(plain, coordinates) == modal_consistency_score(plain, coordinates) == 1.0

    order = keyword_read_order("NETWORK")
    cipher = _encode_coordinates(columnar_encipher(stream, order))
    restored = np.empty(cipher.size, dtype=np.int8)
    _restore_columns(cipher, np.asarray(order, dtype=np.int8), restored)
    assert np.array_equal(restored, coordinates)


def test_exhaustive_combined_solver_recovers_correct_candidate() -> None:
    square = "PHQGMEAYLNOFDXKRCVSZWBUTI"
    texts = ["ATTACKATONCE" * 3, "DEFENDTHEEASTWALL" * 2]
    texts = [text.replace("J", "I") for text in texts]
    # Equalize the diagnostic candidates without borrowing retrieval order.
    length = min(map(len, texts))
    texts = [text[:length] for text in texts]
    plains = np.asarray([_encode_plain(text) for text in texts])
    _stream, ciphertext = adfgx_encipher(texts[0], square, "GERMAN")
    scores = best_combined_scores(_encode_coordinates(ciphertext), plains, _permutations(6))
    assert scores[0] == 1.0
    assert scores[0] > scores[1]


def test_tie_safe_rank_does_not_favor_diagonal_order() -> None:
    scores = np.ones((3, 3))
    result = tie_safe_retrieval(scores)
    assert result["median_rank"] == 2.0
    assert result["top1_fraction"] == 0.0


def test_all_small_permutation_roundtrips() -> None:
    stream = "ADFGXADFGXADF"
    for order in itertools.permutations(range(4)):
        assert columnar_decipher(columnar_encipher(stream, order), order) == stream
