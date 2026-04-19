import re
import unicodedata

from nameparser import HumanName
from unidecode import unidecode


NOISE_WORDS = {
    "mr", "mrs", "ms", "dr", "prof", "sir", "rev", "jr", "sr",
    "the", "a", "an", "and", "of", "for", "ltd", "llc", "inc",
    "corp", "co", "company", "group", "holdings", "international",
    "enterprises", "services", "solutions",
}


def transliterate(text: str) -> str:
    """
    Convert unicode characters to closest ASCII equivalent.
    Vladímir → Vladimir, Ólafur → Olafur.
    Also normalizes unicode combining characters first.
    """
    normalized = unicodedata.normalize("NFKD", text)
    return unidecode(normalized)


def strip_noise(tokens: list[str]) -> list[str]:
    """
    Remove titles, common suffixes, and filler words that add
    noise to matching. 'Dr. Vladimir Putin Jr.' → ['vladimir', 'putin']
    """
    return [t for t in tokens if t not in NOISE_WORDS and len(t) > 1]


def normalize_name(raw: str) -> str:
    """
    Full normalization pipeline for a single name string.

    Steps:
    1. Transliterate unicode to ASCII
    2. Lowercase
    3. Remove punctuation except spaces
    4. Tokenize
    5. Strip noise words
    6. Sort tokens alphabetically (so 'Putin Vladimir' == 'Vladimir Putin')
    7. Rejoin

    The sort step is the key insight: order-independent matching means
    'Last, First' and 'First Last' both normalize to the same string.
    """
    if not raw or not raw.strip():
        return ""

    text = transliterate(raw)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    tokens = strip_noise(tokens)

    if not tokens:
        return raw.lower().strip()

    tokens.sort()
    return " ".join(tokens)


def normalize_human_name(raw: str) -> str:
    """
    Uses nameparser to intelligently split a human name before normalizing.
    Better than raw tokenization for names with prefixes like 'van', 'de', 'al'.
    Falls back to normalize_name if parsing yields nothing useful.
    """
    parsed = HumanName(raw)

    parts = []
    if parsed.first:
        parts.append(parsed.first)
    if parsed.middle:
        parts.append(parsed.middle)
    if parsed.last:
        parts.append(parsed.last)

    if not parts:
        return normalize_name(raw)

    reconstructed = " ".join(parts)
    return normalize_name(reconstructed)


def normalize_org_name(raw: str) -> str:
    """
    Organization names need slightly different treatment —
    nameparser is designed for humans, so we use the base normalizer.
    The noise word list strips 'Ltd', 'Inc', 'Corp' etc so
    'Acme Corp Ltd' and 'Acme Corporation' normalize closer together.
    """
    return normalize_name(raw)


def get_normalizer(entity_type: str | None):
    """
    Returns the right normalizer function based on entity type.
    Centralizes the routing logic so callers don't need to know the detail.
    """
    if entity_type and entity_type.lower() in ("organization", "org", "company"):
        return normalize_org_name
    return normalize_human_name