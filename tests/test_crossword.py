import pytest

from minerva_travel.crossword import CrosswordGenerationError, build_crossword

TRIP_CLUES = [
    ("Paris", "A cidade onde fica a Torre Eiffel"),
    ("Franca", "O pais desta viagem"),
    ("Eiffel", "O sobrenome de quem projetou a torre"),
    ("Viagem", "O que a familia esta fazendo"),
    ("Mapa", "Onde a gente ve onde fica cada lugar"),
    ("Mala", "Onde a roupa vai para a viagem"),
]


def test_every_answer_lands_on_the_grid_with_its_own_clue():
    crossword = build_crossword(TRIP_CLUES)

    assert 4 <= len(crossword.entries) <= 8
    assert all(entry.clue for entry in crossword.entries)
    letters = crossword.letters
    for entry in crossword.entries:
        for offset, letter in enumerate(entry.answer):
            column = entry.column + (offset if entry.across else 0)
            row = entry.row + (0 if entry.across else offset)
            assert letters[(column, row)] == letter


def test_the_grid_is_connected_because_every_word_crosses_another():
    crossword = build_crossword(TRIP_CLUES)

    # Uma palavra sem cruzamento vira lacuna solta: a cruzadinha deixaria de
    # ser cruzada e a criança não teria como conferir a resposta.
    for entry in crossword.entries[1:]:
        cells = {
            (
                entry.column + (offset if entry.across else 0),
                entry.row + (0 if entry.across else offset),
            )
            for offset in range(len(entry.answer))
        }
        others = set()
        for other in crossword.entries:
            if other is entry:
                continue
            others |= {
                (
                    other.column + (offset if other.across else 0),
                    other.row + (0 if other.across else offset),
                )
                for offset in range(len(other.answer))
            }
        assert cells & others


def test_words_never_run_into_each_other_side_by_side():
    crossword = build_crossword(TRIP_CLUES)
    letters = crossword.letters

    for entry in crossword.entries:
        before = (
            (entry.column - 1, entry.row) if entry.across else (entry.column, entry.row - 1)
        )
        after = (
            (entry.column + len(entry.answer), entry.row)
            if entry.across
            else (entry.column, entry.row + len(entry.answer))
        )
        assert before not in letters
        assert after not in letters


def test_numbering_reads_top_left_first_like_a_printed_crossword():
    crossword = build_crossword(TRIP_CLUES)

    ordered = sorted(crossword.entries, key=lambda entry: (entry.row, entry.column))
    numbers = [entry.number for entry in ordered]
    assert numbers == sorted(numbers)
    assert min(numbers) == 1


def test_the_grid_fits_inside_the_printable_area():
    crossword = build_crossword(TRIP_CLUES)

    assert 0 < crossword.columns <= 15
    assert 0 < crossword.rows <= 15


def test_too_few_usable_answers_is_refused_instead_of_printed_half_empty():
    with pytest.raises(CrosswordGenerationError):
        build_crossword([("Rio", "curta"), ("Sao", "curta")])
