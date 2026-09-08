import re
from rest_framework.exceptions import ValidationError

# Common English abusive stems / words
ENGLISH_PROFANITY = {
    'fuck', 'fucking', 'fucker', 'shit', 'bullshit', 'asshole', 'bitch',
    'bastard', 'cunt', 'dick', 'pussy', 'slut', 'whore', 'nigger', 'nigga',
    'faggot', 'retard', 'cock', 'blowjob'
}

# Common Hindi / Hinglish abusive stems / words (Romanized)
HINGLISH_PROFANITY = {
    'chutiya', 'chutiye', 'choot', 'chut', 'bhosdike', 'bhosadi', 'bhosadike',
    'bhenchod', 'behenchod', 'madarchod', 'maderchod', 'mc', 'bc', 'bkl', 'mkc',
    'gandu', 'gaand', 'gand', 'lauda', 'loda', 'lavda', 'lodu', 'lund',
    'harami', 'kamina', 'kamine', 'kaminey', 'randi', 'saala', 'raand',
    'tatty', 'tatti', 'jhaat', 'jhat'
}

# Hindi Devanagari profanity
HINDI_DEVANAGARI_PROFANITY = {
    'चूतिया', 'चूतिए', 'चूत', 'भोसड़ी', 'भोसड़ीके', 'भोसडीके', 'मादरचोद', 'बहनचोद',
    'गांड', 'गाण्ड', 'लौड़ा', 'लोड़ा', 'लंड', 'रांड', 'रंडी', 'हरामी', 'कमीना',
    'कमीने', 'झांट'
}

# Leetspeak translation table
LEET_MAP = str.maketrans({
    '@': 'a',
    '4': 'a',
    '$': 's',
    '5': 's',
    '1': 'i',
    '!': 'i',
    '|': 'i',
    '0': 'o',
    '3': 'e',
    '7': 't',
    '+': 't',
    '8': 'b',
})

# Acronym patterns e.g. m.c, m-c, m c, b.c, b-c, b c, b.k.l, m.k.c
ACRONYM_REGEX = re.compile(
    r'(?:\b|[\s.,\-_/])(?:m[\s._\-*]*c|b[\s._\-*]*c|b[\s._\-*]*k[\s._\-*]*l|m[\s._\-*]*k[\s._\-*]*c)(?:\b|[\s.,\-_/]|$)',
    re.IGNORECASE
)

def _normalize_text(text: str) -> str:
    if not text:
        return ''
    return text.lower().translate(LEET_MAP)

def _collapse_repeated(text: str) -> str:
    # Collapse 2+ consecutive identical characters down to 1
    return re.sub(r'(.)\1+', r'\1', text)

def _strip_interstitial(text: str) -> str:
    return re.sub(r'[^a-z0-9\u0900-\u097F]', '', text)

def contains_profanity(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False

    norm = _normalize_text(text)

    # Check acronyms (e.g. m.c, b.c, b.k.l) before collapsing
    if ACRONYM_REGEX.search(norm):
        return True

    collapsed = _collapse_repeated(norm)

    # 1. Check direct word boundaries in standard tokenized text
    tokens = re.findall(r'[a-z0-9\u0900-\u097F]+', collapsed)
    for token in tokens:
        if token in ENGLISH_PROFANITY or token in HINGLISH_PROFANITY or token in HINDI_DEVANAGARI_PROFANITY:
            return True

    # 2. Check compressed version without punctuation or spaces for obfuscated variations
    compact = _strip_interstitial(collapsed)
    for bad in ['bhenchod', 'behenchod', 'madarchod', 'chutiya', 'bhosdike', 'gandu', 'lauda', 'chut', 'fuck', 'bitch', 'asshole']:
        if bad in compact:
            return True

    for bad_dev in HINDI_DEVANAGARI_PROFANITY:
        if bad_dev in compact:
            return True

    return False

def validate_clean_content(text: str, field_name: str = 'Content'):
    if contains_profanity(text):
        raise ValidationError({
            field_name: f'{field_name} contains inappropriate or prohibited language. Please keep community posts respectful.'
        })
