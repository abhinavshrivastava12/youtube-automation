"""
hindi_transliterate.py
======================
Converts Hindi Devanagari text to Hinglish (Roman script).
Pure Python — no external libraries needed.

Examples:
  स्कूल चलो → school chalo
  बिल्ली मौसी → billi mausi
  चंदा मामा → chanda mama
"""

# ── Character maps ────────────────────────────────────────────────────────────

# Independent vowels
VOWELS = {
    'अ': 'a',   'आ': 'aa',  'इ': 'i',   'ई': 'ee',
    'उ': 'u',   'ऊ': 'oo',  'ए': 'e',   'ऐ': 'ai',
    'ओ': 'o',   'औ': 'au',  'ऋ': 'ri',  'ॠ': 'ri',
    'अं': 'an', 'अः': 'ah',
}

# Dependent vowel signs (matras)
MATRAS = {
    'ा': 'aa', 'ि': 'i',  'ी': 'ee', 'ु': 'u',
    'ू': 'oo', 'े': 'e',  'ै': 'ai', 'ो': 'o',
    'ौ': 'au', 'ृ': 'ri', 'ं': 'n',  'ः': 'h',
    'ँ': 'n',  '्': '',    # halant removes inherent 'a'
    '़': '',               # nukta (ignore)
}

# Consonants (with inherent 'a')
CONSONANTS = {
    'क': 'ka',  'ख': 'kha', 'ग': 'ga',  'घ': 'gha', 'ङ': 'nga',
    'च': 'cha', 'छ': 'chha','ज': 'ja',  'झ': 'jha', 'ञ': 'nya',
    'ट': 'ta',  'ठ': 'tha', 'ड': 'da',  'ढ': 'dha', 'ण': 'na',
    'त': 'ta',  'थ': 'tha', 'द': 'da',  'ध': 'dha', 'न': 'na',
    'प': 'pa',  'फ': 'pha', 'ब': 'ba',  'भ': 'bha', 'म': 'ma',
    'य': 'ya',  'र': 'ra',  'ल': 'la',  'व': 'va',
    'श': 'sha', 'ष': 'sha', 'स': 'sa',  'ह': 'ha',
    'ळ': 'la',  'क्ष': 'ksha', 'त्र': 'tra', 'ज्ञ': 'gya',
    # Nukta variants
    'ख़': 'kha', 'ग़': 'ga', 'ज़': 'za', 'ड़': 'da', 'ढ़': 'dha',
    'फ़': 'fa',  'य़': 'ya',
}

# Common words — direct override for accuracy (most common Hindi words)
WORD_DICT = {
    # School song words
    'स्कूल': 'school', 'चलो': 'chalo', 'पढ़ने': 'padhne',
    'पढ़ाई': 'padhai', 'किताब': 'kitaab', 'कलम': 'kalam',
    # Common words
    'है': 'hai', 'हैं': 'hain', 'और': 'aur', 'का': 'ka', 'की': 'ki',
    'के': 'ke', 'में': 'mein', 'से': 'se', 'को': 'ko', 'पर': 'par',
    'यह': 'yeh', 'वह': 'voh', 'मैं': 'main', 'तुम': 'tum', 'हम': 'hum',
    'आज': 'aaj', 'कल': 'kal', 'अब': 'ab', 'यहाँ': 'yahan', 'वहाँ': 'wahan',
    'नहीं': 'nahi', 'हाँ': 'haan', 'जी': 'ji', 'अच्छा': 'achha',
    # Animals
    'बिल्ली': 'billi', 'मछली': 'machli', 'हाथी': 'haathi', 'घोड़ा': 'ghoda',
    'मोर': 'mor', 'बिल्ली': 'billi', 'चिड़िया': 'chidiya',
    # Rhyme words
    'चंदा': 'chanda', 'मामा': 'mama', 'दूर': 'door', 'तारे': 'taare',
    'आना': 'aana', 'जाना': 'jaana', 'खाना': 'khaana', 'गाना': 'gaana',
    'माँ': 'maa', 'पापा': 'papa', 'नानी': 'naani', 'दादी': 'daadi',
    'बच्चा': 'bachcha', 'बच्चे': 'bachche', 'बच्चों': 'bachchon',
    'सोना': 'sona', 'जागना': 'jaagna', 'रोना': 'rona', 'हँसना': 'hansna',
    'प्यार': 'pyaar', 'दोस्त': 'dost', 'घर': 'ghar', 'स्कूल': 'school',
    'पानी': 'paani', 'दूध': 'doodh', 'रोटी': 'roti', 'मिठाई': 'mithai',
    # Actions
    'आओ': 'aao', 'जाओ': 'jaao', 'खाओ': 'khao', 'पियो': 'piyo',
    'बोलो': 'bolo', 'सुनो': 'suno', 'देखो': 'dekho', 'करो': 'karo',
    'लाओ': 'laao', 'दो': 'do', 'लो': 'lo', 'रहो': 'raho',
    # Numbers
    'एक': 'ek', 'दो': 'do', 'तीन': 'teen', 'चार': 'chaar', 'पाँच': 'paanch',
    'छह': 'chhah', 'सात': 'saat', 'आठ': 'aath', 'नौ': 'nau', 'दस': 'das',
    # Common phrases
    'नया': 'naya', 'पुराना': 'purana', 'बड़ा': 'bada', 'छोटा': 'chhota',
    'अच्छी': 'achhi', 'बुरी': 'buri', 'सुंदर': 'sundar', 'प्यारी': 'pyari',
    'ज्ञान': 'gyan', 'रोशनी': 'roshni', 'उजाला': 'ujala', 'अँधेरा': 'andhera',
    'दोस्त': 'dost', 'दोस्ती': 'dosti', 'मिलकर': 'milkar', 'साथ': 'saath',
    # School chalo specific
    'नए': 'naye', 'बनाना': 'banana', 'दोस्त': 'dost',
}


def _is_devanagari(ch):
    return '\u0900' <= ch <= '\u097F'


def _transliterate_word(word):
    """Transliterate a single Devanagari word to Hinglish."""
    # Direct lookup first
    if word in WORD_DICT:
        return WORD_DICT[word]

    result = []
    i = 0
    n = len(word)

    while i < n:
        ch = word[i]

        # Check 2-char combos first (conjuncts)
        if i + 1 < n and word[i:i+2] in CONSONANTS:
            base = CONSONANTS[word[i:i+2]]
            i += 2
        elif ch in CONSONANTS:
            base = CONSONANTS[ch]
            i += 1
        elif ch in VOWELS:
            result.append(VOWELS[ch])
            i += 1
            continue
        elif ch in MATRAS:
            result.append(MATRAS[ch])
            i += 1
            continue
        elif ch == '\u200d':  # zero-width joiner
            i += 1
            continue
        else:
            # Non-Devanagari character (number, punctuation, etc.)
            result.append(ch)
            i += 1
            continue

        # base is a consonant — check for following matra or halant
        if i < n and word[i] in MATRAS:
            matra = MATRAS[word[i]]
            i += 1
            if matra == '':
                # Halant — strip the inherent 'a' from base
                result.append(base[:-1] if base.endswith('a') else base)
            else:
                result.append(base[:-1] + matra if base.endswith('a') else base + matra)
        else:
            result.append(base)  # inherent 'a' stays

    return ''.join(result)


def hindi_to_hinglish(text):
    """
    Convert a full Hindi string to Hinglish.
    Non-Hindi words (already in English/Roman) are left as-is.
    """
    if not text:
        return text

    # Check if text has any Devanagari at all
    if not any(_is_devanagari(c) for c in text):
        return text  # already Roman

    words = text.split()
    result = []
    for word in words:
        # Strip punctuation around word
        leading  = ''
        trailing = ''
        core = word
        while core and not _is_devanagari(core[0]) and not core[0].isalpha():
            leading += core[0]; core = core[1:]
        while core and not _is_devanagari(core[-1]) and not core[-1].isalpha():
            trailing = core[-1] + trailing; core = core[:-1]

        if any(_is_devanagari(c) for c in core):
            converted = _transliterate_word(core)
            result.append(leading + converted + trailing)
        else:
            result.append(word)

    return ' '.join(result)


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    tests = [
        "स्कूल चलो स्कूल चलो",
        "पढ़ने जाना है",
        "नए दोस्त बनाना है",
        "ज्ञान की रोशनी लाना है",
        "बिल्ली मौसी क्या खाओगी",
        "चंदा मामा दूर के",
        "टिमटिम करते तारे हैं",
        "मछली जल की रानी है",
        "हाथी राजा कहाँ चले",
        "Johny Johny Yes Papa",   # already English — should stay
        "school chalo",           # already hinglish
    ]
    for t in tests:
        print(f"  {t!r:45s} → {hindi_to_hinglish(t)!r}")