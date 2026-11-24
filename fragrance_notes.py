"""
Fragrance note detection, shared by the scraper and the dashboard.

Matching is whole-word in both English and Arabic. Arabic needs care:
a plain substring search for "عود" (oud) also hits "السعودية" (Saudi),
which inflated note counts in the first version of the dashboard.
Here an Arabic note only matches when it stands as its own word,
optionally with the article "ال" and a one-letter prefix (و / ب / ل / ف / ك).
"""

from __future__ import annotations

import re

# English label -> (English keywords, Arabic keywords)
NOTES: dict[str, tuple[list[str], list[str]]] = {
    "Oud":          (["oud", "agarwood"],          ["عود"]),
    "Amber":        (["amber"],                    ["عنبر"]),
    "Musk":         (["musk"],                     ["مسك"]),
    "Rose":         (["rose", "roses"],            ["ورد", "الورود", "ورود"]),
    "Frankincense": (["frankincense", "incense", "bakhoor", "bukhoor"], ["لبان", "بخور"]),
    "Saffron":      (["saffron"],                  ["زعفران"]),
    "Vanilla":      (["vanilla"],                  ["فانيليا", "فانيلا"]),
    "Patchouli":    (["patchouli"],                ["باتشولي", "باتشولى"]),
    "Jasmine":      (["jasmine"],                  ["ياسمين"]),
    "Cardamom":     (["cardamom"],                 ["هيل", "حبهان"]),
    "Sandalwood":   (["sandalwood", "sandal"],     ["صندل"]),
    "Lavender":     (["lavender"],                 ["لافندر", "خزامى"]),
    "Leather":      (["leather"],                  ["جلد", "الجلود"]),
    "Bergamot":     (["bergamot"],                 ["برغموت", "برجموت"]),
    "Citrus":       (["citrus", "lemon", "orange"], ["حمضيات", "ليمون", "برتقال"]),
    "Woods":        (["woody", "woods", "cedar"],  ["أخشاب", "اخشاب", "خشب", "خشبي"]),
    "Tobacco":      (["tobacco"],                  ["تبغ"]),
    "Coffee":       (["coffee"],                   ["قهوة"]),
    "Honey":        (["honey"],                    ["عسل"]),
    "Pepper":       (["pepper"],                   ["فلفل"]),
}

_AR_LETTERS = "ء-ي"
_AR_PREFIX = r"(?:[وبلفك]?ال|[وبلفك])?"


def _ar_pattern(word: str) -> str:
    return rf"(?<![{_AR_LETTERS}]){_AR_PREFIX}{re.escape(word)}(?![{_AR_LETTERS}])"


def _en_pattern(word: str) -> str:
    return rf"\b{re.escape(word)}\b"


_COMPILED: dict[str, re.Pattern[str]] = {
    label: re.compile(
        "|".join([_en_pattern(w) for w in en] + [_ar_pattern(w) for w in ar]),
        flags=re.IGNORECASE,
    )
    for label, (en, ar) in NOTES.items()
}


def find_notes(text: str | None) -> list[str]:
    """Return the note labels mentioned in `text`, in NOTES order."""
    if not text or not isinstance(text, str):
        return []
    return [label for label, rx in _COMPILED.items() if rx.search(text)]
