"""Geradores determinísticos de quebra-cabeças de letras para as atividades.

Tudo aqui é função pura com semente: o mesmo pedido gera sempre o mesmo
caderno, então reimprimir um guia não muda o enigma que a criança já
resolveu. Nada consulta provedor externo — o custo é zero e a resposta é
sempre verificável.
"""

import random
import unicodedata
from dataclasses import dataclass

ANAGRAM_MIN_WORDS = 3
ANAGRAM_MAX_WORDS = 5
ANAGRAM_MIN_LENGTH = 4
ANAGRAM_MAX_LENGTH = 14

CRYPTOGRAM_MAX_LENGTH = 62
CRYPTOGRAM_MIN_LETTERS = 8
# Letras entregues de graça na legenda. Sem elas, decifrar vira força bruta;
# com muitas, a frase se lê sozinha.
CRYPTOGRAM_FREE_LETTERS = 3


class PuzzleGenerationError(ValueError):
    """The supplied vocabulary cannot produce a solvable puzzle."""


@dataclass(frozen=True)
class AnagramEntry:
    scrambled: str
    answer: str

    @property
    def hint(self) -> str:
        """First letter, printed under the answer boxes."""
        return self.answer[0]


@dataclass(frozen=True)
class Cryptogram:
    phrase: str
    codes: tuple[tuple[str, int], ...]
    legend: tuple[tuple[str, int], ...]
    revealed: tuple[str, ...]


# NFD não desfaz ligaduras, então "Sacré-Cœur" chegaria com "Œ" à grade e a
# criança teria de escrever uma letra que não existe no alfabeto dela.
LIGATURES = str.maketrans({"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE", "ß": "ss"})


def normalize_puzzle_word(word: str) -> str:
    """Reduce a place name to the printable A-Z letters a child fills in."""

    expanded = str(word).translate(LIGATURES)
    decomposed = unicodedata.normalize("NFD", expanded)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return "".join(char for char in without_accents.upper() if char.isascii() and char.isalpha())


def build_anagrams(words: list[str], *, seed: str) -> list[AnagramEntry]:
    """Scramble travel words into anagrams the child unscrambles.

    Uma palavra que sai igual à original não é enigma, então embaralhamos de
    novo até mudar — e descartamos a palavra se ela não puder mudar.
    """

    rng = random.Random(f"anagram:{seed}")
    entries: list[AnagramEntry] = []
    seen: set[str] = set()
    for word in words:
        answer = normalize_puzzle_word(word)
        if not ANAGRAM_MIN_LENGTH <= len(answer) <= ANAGRAM_MAX_LENGTH or answer in seen:
            continue
        scrambled = _scramble(answer, rng)
        if scrambled is None:
            continue
        seen.add(answer)
        entries.append(AnagramEntry(scrambled=scrambled, answer=answer))
        if len(entries) == ANAGRAM_MAX_WORDS:
            break
    if len(entries) < ANAGRAM_MIN_WORDS:
        raise PuzzleGenerationError("Não há palavras suficientes para montar os anagramas.")
    return entries


def _scramble(answer: str, rng: random.Random) -> str | None:
    if len(set(answer)) == 1:
        return None
    letters = list(answer)
    for _attempt in range(20):
        rng.shuffle(letters)
        candidate = "".join(letters)
        if candidate != answer:
            return candidate
    return None


def build_cryptogram(phrase: str, *, seed: str) -> Cryptogram:
    """Encode a short factual sentence as numbers with a partial legend."""

    normalized = " ".join(str(phrase).split())
    if not normalized or len(normalized) > CRYPTOGRAM_MAX_LENGTH:
        raise PuzzleGenerationError("A frase do criptograma tem tamanho inválido.")

    stripped = "".join(
        char
        for char in unicodedata.normalize("NFD", normalized.translate(LIGATURES).upper())
        if not unicodedata.combining(char)
    )
    if any(char != " " and not char.isalpha() for char in stripped):
        raise PuzzleGenerationError("A frase do criptograma só aceita letras e espaços.")
    used = sorted({char for char in stripped if char.isalpha()})
    if len(used) < CRYPTOGRAM_MIN_LETTERS:
        raise PuzzleGenerationError("A frase do criptograma é curta demais para decifrar.")

    rng = random.Random(f"cryptogram:{seed}")
    numbers = list(range(1, len(used) + 1))
    rng.shuffle(numbers)
    cipher = dict(zip(used, numbers, strict=True))

    revealed = tuple(sorted(rng.sample(used, k=min(CRYPTOGRAM_FREE_LETTERS, len(used)))))
    return Cryptogram(
        phrase=stripped,
        codes=tuple((char, cipher[char] if char != " " else 0) for char in stripped),
        legend=tuple((char, cipher[char]) for char in used),
        revealed=revealed,
    )
