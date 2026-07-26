import pytest

from minerva_travel.puzzles import (
    CRYPTOGRAM_FREE_LETTERS,
    PuzzleGenerationError,
    build_anagrams,
    build_cryptogram,
    normalize_puzzle_word,
)

TRIP_WORDS = ["Torre", "Eiffel", "Paris", "França", "Viagem"]


def test_anagrams_scramble_every_word_and_keep_the_answer_recoverable():
    entries = build_anagrams(TRIP_WORDS, seed="eiffel")

    assert 3 <= len(entries) <= 5
    for entry in entries:
        assert entry.scrambled != entry.answer
        assert sorted(entry.scrambled) == sorted(entry.answer)
        assert entry.hint == entry.answer[0]


def test_anagrams_are_stable_for_the_same_seed_and_differ_across_seeds():
    first = build_anagrams(TRIP_WORDS, seed="eiffel")
    again = build_anagrams(TRIP_WORDS, seed="eiffel")
    other = build_anagrams(TRIP_WORDS, seed="louvre")

    # Reimprimir o mesmo guia não pode trocar o enigma já resolvido.
    assert [entry.scrambled for entry in first] == [entry.scrambled for entry in again]
    assert [entry.scrambled for entry in first] != [entry.scrambled for entry in other]


def test_anagrams_drop_accents_and_words_that_cannot_be_scrambled():
    entries = build_anagrams(["França", "AAAA", "Roma", "Sé", "Louvre"], seed="mix")

    answers = [entry.answer for entry in entries]
    assert "FRANCA" in answers
    assert "AAAA" not in answers  # uma única letra repetida nunca embaralha
    assert "SE" not in answers  # curta demais para virar enigma


def test_anagrams_refuse_to_build_without_enough_vocabulary():
    with pytest.raises(PuzzleGenerationError):
        build_anagrams(["Sé", "Rio"], seed="curto")


def test_cryptogram_encodes_every_letter_consistently_and_keeps_spaces():
    puzzle = build_cryptogram("A torre tem tres andares", seed="eiffel")

    assert puzzle.phrase == "A TORRE TEM TRES ANDARES"
    by_letter = {}
    for char, code in puzzle.codes:
        if char == " ":
            assert code == 0
            continue
        by_letter.setdefault(char, code)
        assert by_letter[char] == code
    # Duas letras diferentes nunca podem compartilhar o mesmo número.
    assert len(set(by_letter.values())) == len(by_letter)


def test_cryptogram_reveals_a_few_letters_so_a_child_can_start():
    puzzle = build_cryptogram("A torre tem tres andares", seed="eiffel")

    assert len(puzzle.revealed) == CRYPTOGRAM_FREE_LETTERS
    legend_letters = {letter for letter, _code in puzzle.legend}
    assert set(puzzle.revealed) <= legend_letters


def test_cryptogram_rejects_phrases_it_cannot_print_or_solve():
    for phrase in ("", "Custa 30 euros!", "Oi ola", "x" * 80):
        with pytest.raises(PuzzleGenerationError):
            build_cryptogram(phrase, seed="qualquer")


def test_normalize_puzzle_word_strips_accents_punctuation_and_ligatures():
    # "Œ" não existe no alfabeto que a criança escreve nas caixinhas.
    assert normalize_puzzle_word("Sacré-Cœur") == "SACRECOEUR"
    assert normalize_puzzle_word("São Paulo") == "SAOPAULO"
