from minerva_travel.word_search import build_word_search_grid, normalize_word_for_grid


def test_normalize_word_for_grid_strips_accents_and_symbols():
    assert normalize_word_for_grid("França") == "FRANCA"
    assert normalize_word_for_grid("Torre Eiffel") == "TORREEIFFEL"
    assert normalize_word_for_grid("dia 1!") == "DIA"


def test_build_word_search_grid_hides_words_in_rows_or_columns():
    rows, placed = build_word_search_grid(
        ["França", "Torre", "familia", "aventura"],
        seed="custom-paris:torre-eiffel",
    )

    assert len(rows) == 10
    assert all(len(row) == 10 for row in rows)
    assert set(placed) == {"FRANCA", "TORRE", "FAMILIA", "AVENTURA"}

    columns = ["".join(row[index] for row in rows) for index in range(10)]
    searchable = rows + columns
    for word in placed:
        assert any(word in line for line in searchable), f"{word} nao encontrada na grade"


def test_build_word_search_grid_is_deterministic_per_seed():
    first = build_word_search_grid(["Paris", "Torre", "familia"], seed="paris:eiffel")
    second = build_word_search_grid(["Paris", "Torre", "familia"], seed="paris:eiffel")
    different = build_word_search_grid(["Paris", "Torre", "familia"], seed="outra-seed")

    assert first == second
    assert first != different


def test_build_word_search_grid_skips_words_too_long_or_short():
    rows, placed = build_word_search_grid(
        ["ab", "palavramuitocomprida", "VIAGEM"],
        seed="seed",
    )

    assert placed == ["VIAGEM"]
    assert len(rows) == 10
