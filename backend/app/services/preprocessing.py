"""
V2 Preprocessing Module: Clean, normalize, and prepare review text
Uses spaCy for lemmatization and stopword removal
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Try loading spaCy; fall back to simple processing if unavailable
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
    logger.info("spaCy model loaded for preprocessing")
except Exception:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available, falling back to basic preprocessing")

# Common English stopwords (fallback when spaCy not available)
BASIC_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "because", "but", "and",
    "or", "if", "while", "about", "up", "this", "that", "these", "those",
    "i", "me", "my", "myself", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "it", "its", "they", "them", "their", "what",
    "which", "who", "whom", "am",
}


def clean_text(text: str) -> str:
    """Remove noise: URLs, emails, special chars, extra whitespace."""
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.!?,;\'-]', '', text)
    text = ' '.join(text.split())
    return text.strip()


def lowercase(text: str) -> str:
    return text.lower()


def remove_stopwords_basic(tokens: List[str]) -> List[str]:
    """Remove stopwords using basic set."""
    return [t for t in tokens if t not in BASIC_STOPWORDS]


def lemmatize_spacy(text: str) -> str:
    """Lemmatize and remove stopwords using spaCy."""
    doc = nlp(text)
    tokens = [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop and not token.is_punct and not token.is_space and len(token.text) > 1
    ]
    return ' '.join(tokens)


def lemmatize_basic(text: str) -> str:
    """Basic lemmatization fallback: lowercase + stopword removal."""
    tokens = text.lower().split()
    tokens = remove_stopwords_basic(tokens)
    return ' '.join(tokens)


def preprocess_review(text: str) -> str:
    """
    Full preprocessing pipeline for a review:
    1. Clean (remove URLs, emails, special chars)
    2. Lowercase
    3. Lemmatize + remove stopwords (spaCy if available, else basic)

    Returns: preprocessed text string
    """
    if not text or not text.strip():
        return ""

    text = clean_text(text)
    text = lowercase(text)

    if SPACY_AVAILABLE:
        text = lemmatize_spacy(text)
    else:
        text = lemmatize_basic(text)

    return text
