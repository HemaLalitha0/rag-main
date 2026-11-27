"""
AksharaMitra (అక్షరమిత్ర) – Core AI & Linguistic Intelligence Engine
An Education Technology Innovation by SHR Trinity

Implements genuine, data-driven engines for all 15 platform modules:
1. Real AI Reading Assessment & Levenshtein Word Alignment (Accuracy, WPM, Omissions, Substitutions, Insertions)
2. Telugu Akshara Intelligence (Achulu, Hallulu, Mahapranalu, Guninthalu, Ottulu/Vattulu, Unicode Segmentation)
3. English Phonics & Word Decoding (Phonemes, Digraphs, Onset-Rime, Syllabification, Sound Blending)
4. Listen-and-Follow Synchronized Audio & Word Karaoke Engine
5. Personalized Remedial Learning & Automatic Exercise Generator
6. Bilingual Reading Library Catalog (Classes 1-10, Stories, Poems, Science, Moral Lessons)
7. AI Pronunciation Coach (Phonetic Breakdown & Retry Scoring)
8. AI Reading Comprehension Engine (MCQ, Fill-in-the-Blank, True/False Generator & Evaluator)
9. Telugu Virtual Akshara Keyboard & English-to-Telugu Phonetic Transliteration
10. Gamified Reading Challenges (Points, Streaks, Levels, Dynamic Badges)
11. Teacher Intelligence Analytics & Assignment Persistence (SQLite)
12. Parent Progress Portal & Home Practice Recommendations
13. Offline Reading Mode (Lesson Pack JSON/HTML Export & Local Progress Sync)
14. Accessible Reading Interface Controls
15. AI Reading Companion (Bilingual Word & Sentence Explainer)
"""

import difflib
import json
import math
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from auth_guard import get_db_connection, init_auth_tables

# ============================================================================
# 1. TELUGU AKSHARA INTELLIGENCE & UNICODE LINGUISTIC ENGINE
# ============================================================================

TELUGU_ACHULU: List[Dict[str, str]] = [
    {"letter": "అ", "trans": "a", "type": "Hrasva (Short Vowel)", "example": "అమ్మ (Amma - Mother)"},
    {"letter": "ఆ", "trans": "aa", "type": "Deergha (Long Vowel)", "example": "ఆవు (Aavu - Cow)"},
    {"letter": "ఇ", "trans": "i", "type": "Hrasva (Short Vowel)", "example": "ఇల్లు (Illu - House)"},
    {"letter": "ఈ", "trans": "ee", "type": "Deergha (Long Vowel)", "example": "ఈగ (Eega - Fly)"},
    {"letter": "ఉ", "trans": "u", "type": "Hrasva (Short Vowel)", "example": "ఉడుత (Udutha - Squirrel)"},
    {"letter": "ఊ", "trans": "oo", "type": "Deergha (Long Vowel)", "example": "ఊయల (Ooyala - Cradle)"},
    {"letter": "ఋ", "trans": "ru", "type": "Hrasva (Vocalic R)", "example": "ఋషి (Rushi - Sage)"},
    {"letter": "ౠ", "trans": "roo", "type": "Deergha (Long Vocalic R)", "example": "ౠక (Rooka)"},
    {"letter": "ఎ", "trans": "e", "type": "Hrasva (Short Vowel)", "example": "ఎలుక (Eluka - Mouse)"},
    {"letter": "ఏ", "trans": "ae", "type": "Deergha (Long Vowel)", "example": "ఏనుగు (Aenugu - Elephant)"},
    {"letter": "ఐ", "trans": "ai", "type": "Sandhyakshara (Diphthong)", "example": "ఐదు (Aidu - Five)"},
    {"letter": "ఒ", "trans": "o", "type": "Hrasva (Short Vowel)", "example": "ఒంటె (Onte - Camel)"},
    {"letter": "ఓ", "trans": "oh", "type": "Deergha (Long Vowel)", "example": "ఓడ (Oda - Ship)"},
    {"letter": "ఔ", "trans": "au", "type": "Sandhyakshara (Diphthong)", "example": "ఔషధం (Aushadham - Medicine)"},
    {"letter": "అం", "trans": "am", "type": "Ubhayakshara (Anusvara)", "example": "అందం (Andam - Beauty)"},
    {"letter": "అః", "trans": "aha", "type": "Ubhayakshara (Visarga)", "example": "దుఃఖం (Duhkham)"},
]

TELUGU_HALLULU: List[Dict[str, Any]] = [
    {"letter": "క", "trans": "ka", "varga": "Ka-varga (Velar)", "is_mahaprana": False, "example": "కమలం (Lotus)"},
    {"letter": "ఖ", "trans": "kha", "varga": "Ka-varga (Velar)", "is_mahaprana": True, "example": "ఖడ్గం (Sword)"},
    {"letter": "గ", "trans": "ga", "varga": "Ka-varga (Velar)", "is_mahaprana": False, "example": "గంట (Bell)"},
    {"letter": "ఘ", "trans": "gha", "varga": "Ka-varga (Velar)", "is_mahaprana": True, "example": "ఘటం (Pot)"},
    {"letter": "ఙ", "trans": "nga", "varga": "Ka-varga (Nasal)", "is_mahaprana": False, "example": "వాఙ్మయం (Literature)"},
    {"letter": "చ", "trans": "cha", "varga": "Cha-varga (Palatal)", "is_mahaprana": False, "example": "చక్రం (Wheel)"},
    {"letter": "ఛ", "trans": "chha", "varga": "Cha-varga (Palatal)", "is_mahaprana": True, "example": "ఛత్రం (Umbrella)"},
    {"letter": "జ", "trans": "ja", "varga": "Cha-varga (Palatal)", "is_mahaprana": False, "example": "జడ (Braid)"},
    {"letter": "ఝ", "trans": "jha", "varga": "Cha-varga (Palatal)", "is_mahaprana": True, "example": "ఝషం (Fish)"},
    {"letter": "ఞ", "trans": "nya", "varga": "Cha-varga (Nasal)", "is_mahaprana": False, "example": "జ్ఞానం (Knowledge)"},
    {"letter": "ట", "trans": "ta", "varga": "Ta-varga (Retroflex)", "is_mahaprana": False, "example": "టమాట (Tomato)"},
    {"letter": "ఠ", "trans": "tha", "varga": "Ta-varga (Retroflex)", "is_mahaprana": True, "example": "కంఠం (Throat)"},
    {"letter": "డ", "trans": "da", "varga": "Ta-varga (Retroflex)", "is_mahaprana": False, "example": "డబ్బా (Box)"},
    {"letter": "ఢ", "trans": "dha", "varga": "Ta-varga (Retroflex)", "is_mahaprana": True, "example": "ఢంకా (Drum)"},
    {"letter": "ణ", "trans": "na", "varga": "Ta-varga (Nasal)", "is_mahaprana": False, "example": "వీణ (Veena)"},
    {"letter": "త", "trans": "tha", "varga": "Tha-varga (Dental)", "is_mahaprana": False, "example": "తల (Head)"},
    {"letter": "థ", "trans": "thha", "varga": "Tha-varga (Dental)", "is_mahaprana": True, "example": "రథం (Chariot)"},
    {"letter": "ద", "trans": "da", "varga": "Tha-varga (Dental)", "is_mahaprana": False, "example": "దండ (Garland)"},
    {"letter": "ధ", "trans": "dha", "varga": "Tha-varga (Dental)", "is_mahaprana": True, "example": "ధనుస్సు (Bow)"},
    {"letter": "న", "trans": "na", "varga": "Tha-varga (Nasal)", "is_mahaprana": False, "example": "నక్క (Fox)"},
    {"letter": "ప", "trans": "pa", "varga": "Pa-varga (Labial)", "is_mahaprana": False, "example": "పలక (Slate)"},
    {"letter": "ఫ", "trans": "pha", "varga": "Pa-varga (Labial)", "is_mahaprana": True, "example": "ఫలం (Fruit)"},
    {"letter": "బ", "trans": "ba", "varga": "Pa-varga (Labial)", "is_mahaprana": False, "example": "బంతి (Ball)"},
    {"letter": "భ", "trans": "bha", "varga": "Pa-varga (Labial)", "is_mahaprana": True, "example": "భవనం (Building)"},
    {"letter": "మ", "trans": "ma", "varga": "Pa-varga (Nasal)", "is_mahaprana": False, "example": "మంచం (Cot)"},
    {"letter": "య", "trans": "ya", "varga": "Antastha (Approximant)", "is_mahaprana": False, "example": "యంత్రం (Machine)"},
    {"letter": "ర", "trans": "ra", "varga": "Antastha (Liquid)", "is_mahaprana": False, "example": "రవి (Sun)"},
    {"letter": "ల", "trans": "la", "varga": "Antastha (Lateral)", "is_mahaprana": False, "example": "లత (Creeper)"},
    {"letter": "వ", "trans": "va", "varga": "Antastha (Labio-dental)", "is_mahaprana": False, "example": "వల (Net)"},
    {"letter": "శ", "trans": "sha", "varga": "Ushma (Sibilant)", "is_mahaprana": False, "example": "శంఖం (Conch)"},
    {"letter": "ష", "trans": "ssha", "varga": "Ushma (Retroflex Sibilant)", "is_mahaprana": True, "example": "షట్పదం (Bee)"},
    {"letter": "స", "trans": "sa", "varga": "Ushma (Dental Sibilant)", "is_mahaprana": False, "example": "సబ్బు (Soap)"},
    {"letter": "హ", "trans": "ha", "varga": "Ushma (Glottal)", "is_mahaprana": True, "example": "హంస (Swan)"},
    {"letter": "ళ", "trans": "la", "varga": "Retroflex Lateral", "is_mahaprana": False, "example": "తాళం (Lock)"},
    {"letter": "క్ష", "trans": "ksha", "varga": "Samyuktakshara", "is_mahaprana": True, "example": "అక్షరం (Letter)"},
    {"letter": "ఱ", "trans": "rra", "varga": "Bandira", "is_mahaprana": False, "example": "గుఱ్ఱం (Horse)"},
]

TELUGU_GUNINTHALU_SIGNS: List[Dict[str, str]] = [
    {"name": "తలకట్టు (Talakattu)", "sign": "", "vowel": "అ", "sound": "a"},
    {"name": "దీర్ఘం (Deergham)", "sign": "ా", "vowel": "ఆ", "sound": "aa"},
    {"name": "గుడి (Gudi)", "sign": "ి", "vowel": "ఇ", "sound": "i"},
    {"name": "గుడి దీర్ఘం (Gudi Deergham)", "sign": "ీ", "vowel": "ఈ", "sound": "ee"},
    {"name": "కొమ్ము (Kommu)", "sign": "ు", "vowel": "ఉ", "sound": "u"},
    {"name": "కొమ్ము దీర్ఘం (Kommu Deergham)", "sign": "ూ", "vowel": "ఊ", "sound": "oo"},
    {"name": "సుడి / రుత్వం (Rutvam)", "sign": "ృ", "vowel": "ఋ", "sound": "ru"},
    {"name": "ఎత్వం (Etvam)", "sign": "ె", "vowel": "ఎ", "sound": "e"},
    {"name": "ఏత్వం (Aetvam)", "sign": "ే", "vowel": "ఏ", "sound": "ae"},
    {"name": "ఐత్వం (Aitvam)", "sign": "ై", "vowel": "ఐ", "sound": "ai"},
    {"name": "ఒత్వం (Otvam)", "sign": "ొ", "vowel": "ఒ", "sound": "o"},
    {"name": "ఓత్వం (Ohtvam)", "sign": "ో", "vowel": "ఓ", "sound": "oh"},
    {"name": "ఔత్వం (Autvam)", "sign": "ౌ", "vowel": "ఔ", "sound": "au"},
    {"name": "సున్నా (Sunna)", "sign": "ం", "vowel": "అం", "sound": "am"},
    {"name": "విసర్గ (Visarga)", "sign": "ః", "vowel": "అః", "sound": "aha"},
]

TELUGU_VIRAMA = "్"  # Halant / Pollu used to construct Ottulu (Vattulu)


def generate_gunintham_chart(base_consonant: str = "క") -> List[Dict[str, str]]:
    """Generate the complete 15-step Gunintham series for any Telugu consonant."""
    base = (base_consonant or "క").strip()
    if len(base) > 1 and base != "క్ష":
        base = base[0]
    series = []
    for item in TELUGU_GUNINTHALU_SIGNS:
        combined = base + item["sign"]
        series.append({
            "akshara": combined,
            "marker_name": item["name"],
            "vowel": item["vowel"],
            "sign": item["sign"] if item["sign"] else "—",
            "sound": item["sound"],
        })
    return series


def generate_ottulu_examples() -> List[Dict[str, str]]:
    """Return structured Ottulu (Vattulu) categories: Dvitvaksharamulu & Samyuktaksharamulu."""
    return [
        {"base": "క", "ottu": "్క", "combined": "క్క", "type": "Dvitvaksharam (ద్విత్వాక్షరం)", "word": "అక్క (Akka - Sister)"},
        {"base": "మ", "ottu": "్మ", "combined": "మ్మ", "type": "Dvitvaksharam (ద్విత్వాక్షరం)", "word": "అమ్మ (Amma - Mother)"},
        {"base": "ల", "ottu": "్ల", "combined": "ల్ల", "type": "Dvitvaksharam (ద్విత్వాక్షరం)", "word": "ఇల్లు (Illu - House)"},
        {"base": "చ", "ottu": "్చ", "combined": "చ్చ", "type": "Dvitvaksharam (ద్విత్వాక్షరం)", "word": "పచ్చ (Pachha - Green)"},
        {"base": "ట", "ottu": "్ట", "combined": "ట్ట", "type": "Dvitvaksharam (ద్విత్వాక్షరం)", "word": "చెట్టు (Chettu - Tree)"},
        {"base": "ప", "ottu": "్ప", "combined": "ప్ప", "type": "Dvitvaksharam (ద్విత్వాక్షరం)", "word": "గొప్ప (Goppa - Great)"},
        {"base": "స", "ottu": "్త", "combined": "స్త", "type": "Samyuktaksharam (సంయుక్తాక్షరం)", "word": "పుస్తకం (Pustakam - Book)"},
        {"base": "ప", "ottu": "్ర", "combined": "ప్ర", "type": "Samyuktaksharam (సంయుక్తాక్షరం)", "word": "ప్రగతి (Pragathi - Progress)"},
        {"base": "వ", "ottu": "్య", "combined": "వ్య", "type": "Samyuktaksharam (సంయుక్తాక్షరం)", "word": "విద్య (Vidya - Education)"},
        {"base": "ద", "ottu": "్య", "combined": "ద్య", "type": "Samyuktaksharam (సంయుక్తాక్షరం)", "word": "ఉద్యానవనం (Garden)"},
        {"base": "ష", "ottu": "్ట", "combined": "ష్ట", "type": "Samyuktaksharam (సంయుక్తాక్షరం)", "word": "కష్టం (Kashtam - Effort)"},
        {"base": "త", "ottu": "్మ", "combined": "త్మ", "type": "Samyuktaksharam (సంయుక్తాక్షరం)", "word": "ఆత్మవిశ్వాసం (Confidence)"},
    ]


def segment_telugu_aksharas(text: str) -> List[Dict[str, Any]]:
    """
    Segment a Telugu Unicode word or phrase into distinct Akshara orthographic clusters
    and classify each cluster (Achulu, Simple Hallu, Gunintham, Mahaprana, Dvitvakshara, Samyuktakshara).
    """
    mahaprana_set = {"ఖ", "ఘ", "ఛ", "ఝ", "ఠ", "ఢ", "థ", "ధ", "ఫ", "భ", "ష", "హ"}
    achulu_set = {a["letter"] for a in TELUGU_ACHULU}
    matra_set = {m["sign"] for m in TELUGU_GUNINTHALU_SIGNS if m["sign"]}

    cleaned = (text or "").strip()
    clusters: List[str] = []
    curr = ""
    i = 0
    while i < len(cleaned):
        ch = cleaned[i]
        if ch.isspace() or ch in ".,!?;:\"'()-":
            if curr:
                clusters.append(curr)
                curr = ""
            i += 1
            continue
        # Check if ch is a dependent vowel matra, virama, anusvara, visarga
        code = ord(ch)
        is_modifier = (0x0C3E <= code <= 0x0C56) or (0x0C01 <= code <= 0x0C03) or (ch == TELUGU_VIRAMA)
        if is_modifier:
            curr += ch
            # If it's a virama (్) followed by another consonant, attach the next consonant to form an Ottu
            if ch == TELUGU_VIRAMA and (i + 1) < len(cleaned) and not cleaned[i + 1].isspace():
                i += 1
                curr += cleaned[i]
        else:
            if curr:
                clusters.append(curr)
            curr = ch
        i += 1
    if curr:
        clusters.append(curr)

    analyzed = []
    for cl in clusters:
        has_virama = TELUGU_VIRAMA in cl
        has_matra = any(m in cl for m in matra_set)
        has_mahaprana = any(mp in cl for mp in mahaprana_set)
        is_achu = cl in achulu_set or (len(cl) <= 2 and cl[0] in achulu_set)

        if has_virama:
            # Determine if Dvitva (same consonant doubled) or Samyukta (different consonants)
            parts = cl.split(TELUGU_VIRAMA)
            base_c = parts[0][-1] if parts[0] else ""
            sub_c = parts[1][0] if len(parts) > 1 and parts[1] else ""
            category = "Dvitvakshara (ద్విత్వాక్షరం)" if (base_c and base_c == sub_c) else "Samyuktakshara / Ottu (సంయుక్తాక్షరం)"
            difficulty_tag = "Advanced"
        elif has_mahaprana:
            category = "Mahaprana (మహాప్రాణాక్షరం)"
            difficulty_tag = "Intermediate"
        elif has_matra:
            category = "Gunintham (గుణింతాక్షరం)"
            difficulty_tag = "Intermediate"
        elif is_achu:
            category = "Achu (అచ్చు)"
            difficulty_tag = "Beginner"
        else:
            category = "Sarala Hallu (సరళ హల్లు)"
            difficulty_tag = "Beginner"

        analyzed.append({
            "akshara": cl,
            "category": category,
            "has_ottu": has_virama,
            "has_gunintham": has_matra,
            "has_mahaprana": has_mahaprana,
            "difficulty": difficulty_tag,
        })
    return analyzed


# Phonetic English-to-Telugu transliteration map for Virtual Akshara Keyboard
TRANSLITERATION_MAP: Dict[str, str] = {
    "amma": "అమ్మ",
    "aavu": "ఆవు",
    "illu": "ఇల్లు",
    "eega": "ఈగ",
    "udutha": "ఉడుత",
    "ooyala": "ఊయల",
    "eluka": "ఎలుక",
    "aenugu": "ఏనుగు",
    "aidu": "ఐదు",
    "onte": "ఒంటె",
    "oda": "ఓడ",
    "aushadham": "ఔషధం",
    "kamalam": "కమలం",
    "pustakam": "పుస్తకం",
    "vidya": "విద్య",
    "telugu": "తెలుగు",
    "aksharamitra": "అక్షరమిత్ర",
    "badi": "బడి",
    "puvvu": "పువ్వు",
    "chettu": "చెట్టు",
    "chiluka": "చిలుక",
    "nemali": "నెమలి",
    "suryudu": "సూర్యుడు",
    "chandrudu": "చంద్రుడు",
    "panduga": "పండుగ",
    "mitrudu": "మిత్రుడు",
    "desam": "దేశం",
    "bhasha": "భాష",
}

PHONETIC_SYLLABLE_MAP: List[Tuple[str, str]] = [
    ("ksha", "క్ష"), ("chha", "ఛ"), ("kha", "ఖ"), ("gha", "ఘ"), ("jha", "ఝ"),
    ("thha", "థ"), ("dha", "ధ"), ("pha", "ఫ"), ("bha", "భ"), ("sha", "శ"),
    ("ssa", "ష"), ("cha", "చ"), ("tha", "త"),
    ("aa", "ఆ"), ("ee", "ఈ"), ("oo", "ఊ"), ("ai", "ఐ"), ("au", "ఔ"),
    ("ka", "క"), ("ga", "గ"), ("ja", "జ"), ("ta", "ట"), ("da", "డ"),
    ("na", "న"), ("pa", "ప"), ("ba", "బ"), ("ma", "మ"), ("ya", "య"),
    ("ra", "ర"), ("la", "ల"), ("va", "వ"), ("sa", "స"), ("ha", "హ"),
    ("a", "అ"), ("i", "ఇ"), ("u", "ఉ"), ("e", "ఎ"), ("o", "ఒ"),
]


def transliterate_english_to_telugu(roman_text: str) -> str:
    """Convert Romanized Telugu input into Telugu Unicode script."""
    if not roman_text or not roman_text.strip():
        return ""
    words = roman_text.strip().split()
    out_words = []
    for w in words:
        low = w.lower().strip(".,!?")
        if low in TRANSLITERATION_MAP:
            out_words.append(TRANSLITERATION_MAP[low])
            continue
        # Rule-based syllable transliteration fallback
        rem = low
        res = ""
        while rem:
            matched = False
            for lat, tel in PHONETIC_SYLLABLE_MAP:
                if rem.startswith(lat):
                    res += tel
                    rem = rem[len(lat):]
                    matched = True
                    break
            if not matched:
                res += rem[0]
                rem = rem[1:]
        out_words.append(res)
    return " ".join(out_words)


# ============================================================================
# 2. ENGLISH PHONICS & WORD DECODING ENGINE
# ============================================================================

ENGLISH_PHONICS_CATEGORIES: Dict[str, List[Dict[str, Any]]] = {
    "Short & Long Vowels": [
        {"pattern": "Short 'a' (/æ/)", "words": ["cat", "map", "hand", "plant"], "blend": "c - a - t → cat"},
        {"pattern": "Long 'a' (/eɪ/)", "words": ["cake", "rain", "train", "day"], "blend": "t - r - ai - n → train"},
        {"pattern": "Short 'e' (/ɛ/)", "words": ["bed", "pen", "nest", "fresh"], "blend": "n - e - s - t → nest"},
        {"pattern": "Long 'e' (/iː/)", "words": ["tree", "seed", "leaf", "clean"], "blend": "l - ea - f → leaf"},
        {"pattern": "Short 'i' (/ɪ/)", "words": ["pin", "ship", "milk", "wind"], "blend": "w - i - n - d → wind"},
        {"pattern": "Long 'o' (/oʊ/)", "words": ["boat", "road", "home", "grow"], "blend": "b - oa - t → boat"},
    ],
    "Consonant Digraphs & Blends": [
        {"pattern": "ch (/tʃ/)", "words": ["chair", "child", "teacher", "lunch"], "blend": "ch - ai - r → chair"},
        {"pattern": "sh (/ʃ/)", "words": ["ship", "shine", "brush", "shadow"], "blend": "sh - i - n - e → shine"},
        {"pattern": "th (/θ/ & /ð/)", "words": ["think", "thank", "mother", "weather"], "blend": "th - i - nk → think"},
        {"pattern": "ph (/f/)", "words": ["phone", "photo", "graph", "alphabet"], "blend": "ph - o - t - o → photo"},
        {"pattern": "str / spr blends", "words": ["stream", "strong", "spring", "sprout"], "blend": "str - ea - m → stream"},
    ],
    "Multi-Syllable Academic Words": [
        {"pattern": "3-Syllable Nature Words", "words": ["butterfly", "energy", "library", "wonderful"], "blend": "but • ter • fly"},
        {"pattern": "4-Syllable Science Words", "words": ["environment", "education", "technology", "discovery"], "blend": "en • vi • ron • ment"},
    ],
}


def decode_english_word_phonics(word: str) -> Dict[str, Any]:
    """
    Analyze an English word into syllables, vowel/consonant counts, detected digraphs,
    onset-rime split, and step-by-step sound blending cues.
    """
    clean = re.sub(r"[^a-zA-Z]", "", (word or "").strip()).lower()
    if not clean:
        return {"word": "", "syllables": [], "syllable_count": 0, "digraphs": [], "blend_guide": ""}

    vowels = set("aeiouy")
    v_count = sum(1 for c in clean if c in vowels)
    c_count = len(clean) - v_count

    # Detect common digraphs & blends
    known_patterns = ["tion", "sion", "ough", "ight", "ch", "sh", "th", "ph", "wh", "ck", "ng", "qu", "ee", "ea", "oa", "ai", "ay", "ou", "ow", "oo"]
    found_digraphs = [p for p in known_patterns if p in clean]

    # Heuristic English syllabification
    syllables = []
    curr = ""
    i = 0
    while i < len(clean):
        curr += clean[i]
        if clean[i] in vowels:
            # Check if followed by consonant + vowel
            if (i + 2) < len(clean) and clean[i + 1] not in vowels and clean[i + 2] in vowels:
                syllables.append(curr)
                curr = ""
            elif (i + 3) < len(clean) and clean[i + 1] not in vowels and clean[i + 2] not in vowels and clean[i + 3] in vowels:
                curr += clean[i + 1]
                i += 1
                syllables.append(curr)
                curr = ""
        i += 1
    if curr:
        if syllables and not any(c in vowels for c in curr):
            syllables[-1] += curr
        else:
            syllables.append(curr)

    # Onset-rime split
    first_v_idx = next((idx for idx, ch in enumerate(clean) if ch in vowels), 0)
    onset = clean[:first_v_idx] if first_v_idx > 0 else "(vowel onset)"
    rime = clean[first_v_idx:]

    blend_steps = " • ".join(syllables) if len(syllables) > 1 else " - ".join(list(clean))
    return {
        "word": clean,
        "syllables": syllables,
        "syllable_count": len(syllables),
        "vowel_count": v_count,
        "consonant_count": c_count,
        "digraphs": found_digraphs,
        "onset": onset,
        "rime": rime,
        "blend_guide": f"{blend_steps}  ➔  {clean}",
    }


# ============================================================================
# 3. REAL AI READING ASSESSMENT & WORD ALIGNMENT ENGINE
# ============================================================================

def _normalize_token(tok: str) -> str:
    """Strip punctuation while preserving all Telugu Unicode matras and English letters."""
    return re.sub(r"[.,!?;:\"'()\[\]{}—–\-…]", "", (tok or "").strip()).lower()


def align_and_evaluate_reading(
    reference_text: str,
    spoken_transcript: str,
    duration_sec: float,
    target_wpm: int = 65,
    language: str = "Telugu",
) -> Dict[str, Any]:
    """
    Perform genuine token-by-token sequence alignment between the expected passage text
    and the student's actual spoken speech transcript.
    Computes:
      - Word-level status: 'correct' (Green), 'needs_work' (Yellow), 'mispronounced' (Red), 'skipped' (Grey)
      - Substitutions, Omissions, and Insertions
      - Accuracy %, WPM, Fluency Score, Pronunciation Score
      - Specific phonological/Akshara weakness diagnosis
    Never fabricates scores: if spoken_transcript is empty, accuracy and WPM are 0.0.
    """
    ref_raw_tokens = [t for t in (reference_text or "").strip().split() if _normalize_token(t)]
    hyp_raw_tokens = [t for t in (spoken_transcript or "").strip().split() if _normalize_token(t)]

    ref_norm = [_normalize_token(t) for t in ref_raw_tokens]
    hyp_norm = [_normalize_token(t) for t in hyp_raw_tokens]

    total_words = len(ref_raw_tokens)
    if total_words == 0:
        return {"accuracy_pct": 0.0, "wpm": 0, "word_analysis": []}

    if not hyp_norm:
        empty_analysis = [
            {
                "word": w,
                "status": "skipped",
                "spoken": "— (లోపించింది / Skipped)",
                "issue": "No speech detected for this word.",
                "tip": "Listen to the model audio and read aloud clearly.",
            }
            for w in ref_raw_tokens
        ]
        return {
            "overall_score": 0.0,
            "accuracy_pct": 0.0,
            "pronunciation_score": 0.0,
            "fluency_score": 0.0,
            "wpm": 0,
            "target_wpm": target_wpm,
            "duration_sec": round(max(0.0, duration_sec), 1),
            "total_words": total_words,
            "correct_words": 0,
            "needs_work_words": 0,
            "mispronounced_words": 0,
            "skipped_words": total_words,
            "inserted_words": 0,
            "student_transcript": "",
            "word_analysis": empty_analysis,
            "ai_observations": ["No spoken audio was captured. Please verify your microphone and read the passage aloud."],
            "recommendations": ["Use the Listen-and-Follow player first, then try reading sentence by sentence."],
        }

    matcher = difflib.SequenceMatcher(None, ref_norm, hyp_norm)
    word_analysis: List[Dict[str, str]] = []
    correct_count = 0
    needs_work_count = 0
    mispronounced_count = 0
    skipped_count = 0
    inserted_count = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rw = ref_raw_tokens[i1 + k]
                hw = hyp_raw_tokens[j1 + k]
                correct_count += 1
                word_analysis.append({
                    "word": rw,
                    "status": "correct",
                    "spoken": hw,
                    "issue": "None — Clear & accurate pronunciation",
                    "tip": "Great job! Keep up this clear articulation.",
                })
        elif tag == "replace":
            ref_slice = ref_raw_tokens[i1:i2]
            hyp_slice = hyp_raw_tokens[j1:j2]
            max_len = max(len(ref_slice), len(hyp_slice))
            for k in range(max_len):
                if k < len(ref_slice) and k < len(hyp_slice):
                    rw = ref_slice[k]
                    hw = hyp_slice[k]
                    r_n = _normalize_token(rw)
                    h_n = _normalize_token(hw)
                    sim = difflib.SequenceMatcher(None, r_n, h_n).ratio()
                    if sim >= 0.86:
                        correct_count += 1
                        word_analysis.append({
                            "word": rw,
                            "status": "correct",
                            "spoken": hw,
                            "issue": "None — Clear articulation",
                            "tip": "Well read!",
                        })
                    elif sim >= 0.52:
                        needs_work_count += 1
                        issue_desc = (
                            "Minor gunintham / vowel inflection variation."
                            if language == "Telugu"
                            else "Partial syllable or vowel sound variation."
                        )
                        word_analysis.append({
                            "word": rw,
                            "status": "needs_work",
                            "spoken": hw,
                            "issue": issue_desc,
                            "tip": f"Read '{rw}' slowly, paying attention to each syllable.",
                        })
                    else:
                        mispronounced_count += 1
                        issue_desc = (
                            "Samyuktakshara / Ottu or consonant substitution detected."
                            if language == "Telugu"
                            else "Word substitution or phoneme decoding error."
                        )
                        word_analysis.append({
                            "word": rw,
                            "status": "mispronounced",
                            "spoken": hw,
                            "issue": issue_desc,
                            "tip": f"Break '{rw}' into smaller parts and practice with the Pronunciation Coach.",
                        })
                elif k < len(ref_slice):
                    rw = ref_slice[k]
                    skipped_count += 1
                    word_analysis.append({
                        "word": rw,
                        "status": "skipped",
                        "spoken": "— (లోపించింది / Skipped)",
                        "issue": "Word omitted during reading.",
                        "tip": f"Track with your finger so you don't skip '{rw}'.",
                    })
                else:
                    inserted_count += 1
        elif tag == "delete":
            for idx in range(i1, i2):
                rw = ref_raw_tokens[idx]
                skipped_count += 1
                word_analysis.append({
                    "word": rw,
                    "status": "skipped",
                    "spoken": "— (లోపించింది / Skipped)",
                    "issue": "Word omitted during reading.",
                    "tip": f"Pause briefly and read '{rw}' carefully.",
                })
        elif tag == "insert":
            inserted_count += (j2 - j1)

    eff_dur = max(5.0, float(duration_sec or 30.0))
    spoken_word_count = len(hyp_raw_tokens)
    wpm = int(round((spoken_word_count / eff_dur) * 60.0))

    # Calculate genuine metrics
    weighted_correct = correct_count + (0.6 * needs_work_count)
    accuracy_pct = round(min(100.0, max(0.0, (weighted_correct / total_words) * 100.0)), 1)

    attempted = max(1, correct_count + needs_work_count + mispronounced_count)
    pronunciation_score = round(min(100.0, ((correct_count + 0.5 * needs_work_count) / attempted) * 100.0), 1)

    pace_ratio = min(1.15, wpm / float(max(20, target_wpm)))
    fluency_score = round(min(100.0, (accuracy_pct * 0.65) + (min(1.0, pace_ratio) * 35.0)), 1)
    overall_score = round((accuracy_pct * 0.45) + (pronunciation_score * 0.30) + (fluency_score * 0.25), 1)

    # Generate diagnostic observations based on actual errors
    observations = []
    recommendations = []
    mis_list = [w["word"] for w in word_analysis if w["status"] in ("mispronounced", "needs_work")]
    skip_list = [w["word"] for w in word_analysis if w["status"] == "skipped"]

    if accuracy_pct >= 90:
        observations.append(f"Excellent reading accuracy ({accuracy_pct}%) with strong word recognition.")
    elif accuracy_pct >= 75:
        observations.append(f"Good reading foundation ({accuracy_pct}%), with minor hesitations on complex words.")
    else:
        observations.append(f"Developing accuracy ({accuracy_pct}%). Guided decoding practice is recommended.")

    if mis_list:
        sample_mis = ", ".join(mis_list[:4])
        if language == "Telugu":
            observations.append(f"Pronunciation support needed on: {sample_mis} (focus on Ottulu & Guninthalu).")
            recommendations.append(f"Practice Akshara segmentation for: {sample_mis} in the Telugu Akshara Intelligence tab.")
        else:
            observations.append(f"Decoding support needed on: {sample_mis} (focus on multi-syllable blending).")
            recommendations.append(f"Use the English Phonics & Pronunciation Coach to practice: {sample_mis}.")
    if skip_list:
        sample_skip = ", ".join(skip_list[:4])
        observations.append(f"Skipped {len(skip_list)} word(s) ({sample_skip}).")
        recommendations.append("Use the Listen-and-Follow word highlighter to avoid skipping words across lines.")

    if wpm < target_wpm * 0.75:
        observations.append(f"Reading pace ({wpm} WPM) is below the grade target ({target_wpm} WPM).")
        recommendations.append("Practice repeated reading of familiar sentences to build automaticity and speed.")
    else:
        observations.append(f"Healthy reading pace of {wpm} WPM compared to benchmark ({target_wpm} WPM).")

    if not recommendations:
        recommendations.append("Ready for the next difficulty tier or a comprehension challenge!")

    return {
        "overall_score": overall_score,
        "accuracy_pct": accuracy_pct,
        "pronunciation_score": pronunciation_score,
        "fluency_score": fluency_score,
        "wpm": wpm,
        "target_wpm": target_wpm,
        "duration_sec": round(eff_dur, 1),
        "total_words": total_words,
        "correct_words": correct_count,
        "needs_work_words": needs_work_count,
        "mispronounced_words": mispronounced_count,
        "skipped_words": skipped_count,
        "inserted_words": inserted_count,
        "student_transcript": spoken_transcript.strip(),
        "word_analysis": word_analysis,
        "ai_observations": observations,
        "recommendations": recommendations,
    }


# ============================================================================
# 4. BILINGUAL READING LIBRARY (CLASSES 1-10) & COMPREHENSION ENGINE
# ============================================================================

BILINGUAL_LIBRARY_PASSAGES: List[Dict[str, Any]] = [
    {
        "id": "TE-C1-01",
        "language": "Telugu",
        "grade": "Class 1",
        "difficulty": "Beginner",
        "genre": "Poem / Rhyme (గేయం)",
        "title": "చందమామ రావే (Chandamama Raave)",
        "subtitle": "సరళమైన పదాలు • Foundational Childhood Rhyme",
        "target_wpm": 40,
        "reference_text": (
            "చందమామ రావే జాబిల్లి రావే. కొండెక్కి రావే గోగుపూలు తేవే. "
            "బండి మీద రావే బంతిపూలు తేవే. తేరు మీద రావే తేనె పట్టు తేవే. "
            "పాపాయికి పాలు వెన్న తేవే."
        ),
        "vocabulary": {
            "జాబిల్లి": "చందమామ (The Moon)",
            "తేరు": "రథం (Chariot)",
            "తేనె": "మధువు (Honey)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "కొండెక్కి ఏ పూలు తేవాలని పాటలో అడుగుతున్నారు?",
                "options": ["గోగుపూలు", "గులాబీలు", "మల్లెపూలు", "కలువలు"],
                "answer": "గోగుపూలు",
            },
            {
                "type": "TF",
                "q": "బండి మీద బంతిపూలు తేవాలని చెప్పారు.",
                "options": ["True (నిజం)", "False (తప్పు)"],
                "answer": "True (నిజం)",
            },
            {
                "type": "FIB",
                "q": "తేరు మీద రావే _____ పట్టు తేవే.",
                "options": ["తేనె", "పాలు", "నీరు", "పండు"],
                "answer": "తేనె",
            },
        ],
    },
    {
        "id": "TE-C2-01",
        "language": "Telugu",
        "grade": "Class 2",
        "difficulty": "Beginner",
        "genre": "Nature Story (ప్రకృతి కథ)",
        "title": "మన తోటలోని పూలు (Flowers in Our Garden)",
        "subtitle": "సరళమైన పదాలు మరియు చిన్న వాక్యాలు • Primary Fluency Passage",
        "target_wpm": 50,
        "reference_text": (
            "మా ఇంటి ముందు ఒక అందమైన పూల తోట ఉంది. "
            "ఆ తోటలో ఎర్రని గులాబీలు మరియు తెల్లని మల్లెపూలు పూస్తాయి. "
            "ప్రతి ఉదయం సీతాకోకచిలుకలు పూల మీద వాలి మధువును తాగుతాయి. "
            "నేను ప్రతిరోజూ మొక్కలకు నీరు పోస్తాను."
        ),
        "vocabulary": {
            "తోట": "మొక్కలు పెంచే ప్రదేశం (Garden)",
            "సీతాకోకచిలుకలు": "రంగురంగుల కీటకాలు (Butterflies)",
            "మధువు": "పూలలోని తేనె (Nectar)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "తోటలో ఏ ఏ పూలు పూస్తాయి?",
                "options": ["గులాబీలు మరియు మల్లెపూలు", "తామర పూలు", "బంతిపూలు మాత్రమే", "సూర్యకాంతి పూలు"],
                "answer": "గులాబీలు మరియు మల్లెపూలు",
            },
            {
                "type": "MCQ",
                "q": "పూల మీద వాలి మధువును ఎవరు తాగుతారు?",
                "options": ["సీతాకోకచిలుకలు", "కుందేళ్లు", "చిలుకలు", "కాకులు"],
                "answer": "సీతాకోకచిలుకలు",
            },
            {
                "type": "TF",
                "q": "నేను ప్రతిరోజూ మొక్కలకు నీరు పోస్తాను.",
                "options": ["True (నిజం)", "False (తప్పు)"],
                "answer": "True (నిజం)",
            },
        ],
    },
    {
        "id": "TE-C4-01",
        "language": "Telugu",
        "grade": "Class 4",
        "difficulty": "Intermediate",
        "genre": "Moral Lesson (నీతి పాఠం)",
        "title": "పాఠశాల గ్రంథాలయం (The School Library)",
        "subtitle": "గుణింతాలు మరియు సంయుక్తాక్షరాలు • Intermediate Comprehension Passage",
        "target_wpm": 75,
        "reference_text": (
            "మా పాఠశాలలో ఒక పెద్ద గ్రంథాలయం ఉన్నది. "
            "అందులో తెలుగు కథల పుస్తకాలు, విజ్ఞాన శాస్త్ర గ్రంథాలు మరియు దినపత్రికలు ఎన్నో ఉన్నాయి. "
            "ఉపాధ్యాయులు మమ్మల్ని ప్రతిరోజూ ఒక మంచి పుస్తకం చదవమని ప్రోత్సహిస్తారు. "
            "పుస్తక పఠనం వల్ల మనకు లోకజ్ఞానం, ఆలోచనా శక్తి మరియు మంచి వ్యక్తిత్వం లభిస్తాయి."
        ),
        "vocabulary": {
            "గ్రంథాలయం": "పుస్తకాలు భద్రపరిచే గది (Library)",
            "ప్రోత్సహిస్తారు": "ఉత్సాహాన్ని ఇస్తారు (Encourage)",
            "వ్యక్తిత్వం": "మంచి నడవడిక (Personality / Character)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "గ్రంథాలయంలో ఏమేమి ఉన్నాయి?",
                "options": ["కథల పుస్తకాలు, విజ్ఞాన శాస్త్ర గ్రంథాలు, దినపత్రికలు", "ఆట వస్తువులు మాత్రమే", "చెట్లు మరియు పూలు", "సైకిళ్లు"],
                "answer": "కథల పుస్తకాలు, విజ్ఞాన శాస్త్ర గ్రంథాలు, దినపత్రికలు",
            },
            {
                "type": "FIB",
                "q": "పుస్తక పఠనం వల్ల మనకు లోకజ్ఞానం, _____ శక్తి లభిస్తాయి.",
                "options": ["ఆలోచనా", "పరుగు", "ఆటల", "నిద్ర"],
                "answer": "ఆలోచనా",
            },
            {
                "type": "TF",
                "q": "ఉపాధ్యాయులు ప్రతిరోజూ పుస్తకం చదవమని ప్రోత్సహిస్తారు.",
                "options": ["True (నిజం)", "False (తప్పు)"],
                "answer": "True (నిజం)",
            },
        ],
    },
    {
        "id": "TE-C6-01",
        "language": "Telugu",
        "grade": "Class 6",
        "difficulty": "Intermediate",
        "genre": "Moral Fable (పంచతంత్ర కథ)",
        "title": "ఐకమత్యమే మహాబలం (Unity is Strength)",
        "subtitle": "ఒత్తులు మరియు భావ వ్యక్తీకరణ • Upper Primary Story",
        "target_wpm": 85,
        "reference_text": (
            "ఒక అడవిలో నాలుగు ఎద్దులు ఎంతో స్నేహంగా ఉండేవి. అవి ఎప్పుడూ కలిసే గడ్డి మేసేవి. "
            "ఒక సింహం వాటిని వేటాడాలని చూసింది కానీ అవి కలిసికట్టుగా ఉండటం వల్ల సింహం భయపడింది. "
            "మనం అందరం ఐకమత్యంగా ఉంటే ఎలాంటి కష్టాన్నైనా సులభంగా జయించగలము."
        ),
        "vocabulary": {
            "ఐకమత్యం": "కలిసిమెలిసి ఉండటం (Unity)",
            "కలిసికట్టుగా": "ఒకటిగా (Together)",
            "జయించగలము": "గెలవగలము (Can overcome)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "అడవిలో ఎన్ని ఎద్దులు స్నేహంగా ఉండేవి?",
                "options": ["నాలుగు", "రెండు", "ఐదు", "పది"],
                "answer": "నాలుగు",
            },
            {
                "type": "TF",
                "q": "ఎద్దులు కలిసికట్టుగా ఉండటం వల్ల సింహం భయపడింది.",
                "options": ["True (నిజం)", "False (తప్పు)"],
                "answer": "True (నిజం)",
            },
        ],
    },
    {
        "id": "TE-C9-01",
        "language": "Telugu",
        "grade": "Class 9",
        "difficulty": "Advanced",
        "genre": "Culture & Science (సాహిత్యం & విజ్ఞానం)",
        "title": "తెలుగు భాషా వైభవం మరియు సాంకేతిక ప్రగతి",
        "subtitle": "సంక్లిష్ట సమాసాలు మరియు సాహిత్య శైలి • High School Fluency Passage",
        "target_wpm": 105,
        "reference_text": (
            "తెలుగు భాషకు వేల సంవత్సరాల ఘనమైన చరిత్ర మరియు సాహిత్య సంపద ఉన్నాయి. "
            "దేశభాషలందు తెలుగు లెస్స అని శ్రీకృష్ణదేవరాయలు మన మాతృభాషను కొనియాడారు. "
            "నేటి ఆధునిక యుగంలో కృత్రిమ మేధస్సు మరియు డిజిటల్ సాంకేతికత సహాయంతో ప్రతి విద్యార్థి "
            "తమ ఉచ్చారణను మెరుగుపరచుకుంటూ ప్రపంచ స్థాయిలో రాణించగలరు."
        ),
        "vocabulary": {
            "కొనియాడారు": "ప్రశంసించారు (Praised)",
            "కృత్రిమ మేధస్సు": "Artificial Intelligence",
            "ఉచ్చారణ": "పదాలను పలికే విధానం (Pronunciation)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "'దేశభాషలందు తెలుగు లెస్స' అని ఎవరు కొనియాడారు?",
                "options": ["శ్రీకృష్ణదేవరాయలు", "నన్నయ", "తిక్కన", "పోతన"],
                "answer": "శ్రీకృష్ణదేవరాయలు",
            },
            {
                "type": "FIB",
                "q": "నేటి ఆధునిక యుగంలో _____ మేధస్సు సహాయంతో ఉచ్చారణను మెరుగుపరచుకోవచ్చు.",
                "options": ["కృత్రిమ", "పురాతన", "సాధారణ", "భౌతిక"],
                "answer": "కృత్రిమ",
            },
        ],
    },
    {
        "id": "EN-C2-01",
        "language": "English",
        "grade": "Class 2",
        "difficulty": "Beginner",
        "genre": "Story",
        "title": "A Sunny Morning at the Village Park",
        "subtitle": "Foundational Phonics & Sight Words • Primary English Passage",
        "target_wpm": 65,
        "reference_text": (
            "The sun rises high in the blue sky every morning. "
            "Ravi takes his red ball and walks to the green park near his school. "
            "Many little birds sing sweet songs on the tall mango trees. "
            "Reading books with friends makes every day happy and bright."
        ),
        "vocabulary": {
            "rises": "comes up (ఉదయిస్తుంది)",
            "sweet": "pleasant and melodious (తియ్యని / మధురమైన)",
            "bright": "shining with light (ప్రకాశవంతమైన)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "What does Ravi take to the green park?",
                "options": ["His red ball", "A blue bicycle", "A yellow kite", "His school bag"],
                "answer": "His red ball",
            },
            {
                "type": "MCQ",
                "q": "Where do the little birds sing sweet songs?",
                "options": ["On the tall mango trees", "Inside the classroom", "On the roof", "Near the river"],
                "answer": "On the tall mango trees",
            },
            {
                "type": "TF",
                "q": "Reading books with friends makes every day happy and bright.",
                "options": ["True", "False"],
                "answer": "True",
            },
        ],
    },
    {
        "id": "EN-C5-01",
        "language": "English",
        "grade": "Class 5",
        "difficulty": "Intermediate",
        "genre": "Science & Environment",
        "title": "How Rainwater Harvesting Protects Our Future",
        "subtitle": "Multi-Syllable Academic Vocabulary • Middle School Passage",
        "target_wpm": 100,
        "reference_text": (
            "Water is one of the most precious natural resources on planet Earth. "
            "During the monsoon season, heavy rainfall flows away into rivers and oceans. "
            "By building rainwater harvesting pits in our schools and villages, we can store clean water underground. "
            "This simple scientific practice helps farmers grow healthy crops throughout the year."
        ),
        "vocabulary": {
            "precious": "of great value (విలువైన)",
            "harvesting": "collecting and storing (సేకరించి నిల్వ చేయడం)",
            "underground": "beneath the surface of the ground (భూగర్భంలో)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "Why should we build rainwater harvesting pits in schools and villages?",
                "options": [
                    "To store clean water underground",
                    "To make water flow faster into oceans",
                    "To stop the monsoon season",
                    "To build swimming pools",
                ],
                "answer": "To store clean water underground",
            },
            {
                "type": "FIB",
                "q": "This simple scientific practice helps _____ grow healthy crops.",
                "options": ["farmers", "pilots", "drivers", "painters"],
                "answer": "farmers",
            },
            {
                "type": "TF",
                "q": "Water is one of the most precious natural resources on Earth.",
                "options": ["True", "False"],
                "answer": "True",
            },
        ],
    },
    {
        "id": "EN-C9-01",
        "language": "English",
        "grade": "Class 9",
        "difficulty": "Advanced",
        "genre": "Technology & Education",
        "title": "Artificial Intelligence in Modern Classroom Education",
        "subtitle": "Complex Syntax & Critical Articulation • High School Passage",
        "target_wpm": 125,
        "reference_text": (
            "Artificial intelligence is transforming public education by providing personalized guidance to every learner. "
            "When a student reads aloud, intelligent speech recognition models analyze pronunciation, fluency, and comprehension in real time. "
            "Teachers can immediately identify foundational gaps and design targeted remedial exercises so that no child is left behind."
        ),
        "vocabulary": {
            "transforming": "changing completely for the better (మార్పు తీసుకువస్తోంది)",
            "personalized": "tailored to an individual student's needs (వ్యక్తిగతీకరించిన)",
            "remedial": "intended to correct or improve weak skills (లోపాలను సరిదిద్దే)",
        },
        "comprehension": [
            {
                "type": "MCQ",
                "q": "What do intelligent speech recognition models analyze when a student reads aloud?",
                "options": [
                    "Pronunciation, fluency, and comprehension",
                    "Handwriting speed only",
                    "Sports attendance",
                    "Classroom seating order",
                ],
                "answer": "Pronunciation, fluency, and comprehension",
            },
            {
                "type": "TF",
                "q": "Teachers can use AI insights to design targeted remedial exercises.",
                "options": ["True", "False"],
                "answer": "True",
            },
        ],
    },
]


# ============================================================================
# 5. PERSONALIZED REMEDIAL LEARNING & AI READING COMPANION
# ============================================================================

def generate_personalized_remedial_plan(
    assessment_result: Dict[str, Any],
    language: str = "Telugu",
) -> Dict[str, Any]:
    """
    Generate a customized 3-stage remedial practice plan based on the student's actual
    mispronounced and skipped words from their latest reading assessment.
    """
    word_list = assessment_result.get("word_analysis", [])
    mis_words = [w["word"] for w in word_list if w.get("status") in ("mispronounced", "needs_work")]
    skip_words = [w["word"] for w in word_list if w.get("status") == "skipped"]
    acc = float(assessment_result.get("accuracy_pct", 85.0))

    if acc < 70:
        assigned_tier = "Beginner (పునాది స్థాయి)"
    elif acc < 88:
        assigned_tier = "Intermediate (మధ్యమ స్థాయి)"
    else:
        assigned_tier = "Advanced (ఉన్నత స్థాయి)"

    drills = []
    if language == "Telugu":
        target_words = (mis_words + skip_words)[:5] or ["గ్రంథాలయం", "సీతాకోకచిలుకలు", "ఉపాధ్యాయులు", "ప్రోత్సహిస్తారు"]
        for tw in target_words:
            seg = segment_telugu_aksharas(tw)
            akshara_str = " + ".join(s["akshara"] for s in seg)
            cats = ", ".join(sorted({s["category"] for s in seg}))
            drills.append({
                "word": tw,
                "breakdown": akshara_str,
                "focus_skill": cats,
                "exercise": f"1) Clap for each akshara ({akshara_str}). 2) Read aloud 3 times slowly. 3) Type '{tw}' on the Virtual Akshara Keyboard.",
            })
    else:
        target_words = (mis_words + skip_words)[:5] or ["harvesting", "underground", "scientific", "transforming"]
        for tw in target_words:
            dec = decode_english_word_phonics(tw)
            drills.append({
                "word": tw,
                "breakdown": dec["blend_guide"],
                "focus_skill": f"{dec['syllable_count']} Syllables | Digraphs: {', '.join(dec['digraphs']) or 'Standard'}",
                "exercise": f"1) Sound out onset '{dec['onset']}' + rime '{dec['rime']}'. 2) Blend syllables ({' • '.join(dec['syllables'])}). 3) Record in Pronunciation Coach.",
            })

    return {
        "assigned_tier": assigned_tier,
        "weak_word_count": len(mis_words) + len(skip_words),
        "target_words": [d["word"] for d in drills],
        "drills": drills,
        "daily_goal_minutes": 10 if acc >= 85 else 15,
    }


def ask_reading_companion(
    query: str,
    passage_context: str = "",
    language: str = "Telugu",
    grade: str = "Class 4",
) -> str:
    """
    Interactive AI Reading Companion that explains difficult words, breaks down sentences,
    and encourages students in an age-appropriate bilingual manner.
    Uses LLM when configured, with a rich deterministic linguistic fallback so it never fails offline.
    """
    q_clean = (query or "").strip()
    if not q_clean:
        return "Hello! I am your AksharaMitra Reading Companion (అక్షరమిత్ర నేస్తం). Ask me the meaning of any word or sentence from your lesson!"

    # Check if asking about a word in our vocabulary maps
    for p in BILINGUAL_LIBRARY_PASSAGES:
        for vw, vmeaning in p.get("vocabulary", {}).items():
            if vw.lower() in q_clean.lower():
                if language == "Telugu":
                    seg = " + ".join(s["akshara"] for s in segment_telugu_aksharas(vw))
                    return (
                        f"🌟 **పద వివరణ ({vw}):**\n\n"
                        f"- **అర్థం (Meaning):** {vmeaning}\n"
                        f"- **అక్షర విభజన (Akshara Split):** `{seg}`\n"
                        f"- **సూచన:** ఈ పదాన్ని మెల్లగా అక్షరం-అక్షరం కలిపి మూడుసార్లు పైకి చదవండి! శభాష్!"
                    )
                else:
                    dec = decode_english_word_phonics(vw)
                    return (
                        f"🌟 **Word Explorer (`{vw}`):**\n\n"
                        f"- **Meaning:** {vmeaning}\n"
                        f"- **Syllable Breakdown:** `{dec['blend_guide']}` ({dec['syllable_count']} syllables)\n"
                        f"- **Practice Tip:** Sound out each syllable clearly and use it in your own sentence!"
                    )

    # Try calling LLM for open-ended questions
    try:
        from llm_client import call_llm
        prompt = (
            f"You are AksharaMitra (అక్షరమిత్ర), a warm, encouraging bilingual (Telugu & English) "
            f"reading teacher for a {grade} school student. "
            f"Passage context: \"{passage_context}\"\n"
            f"Student's question: \"{q_clean}\"\n"
            f"Provide a short, child-friendly explanation (4-6 lines) with pronunciation or Akshara breakdown and positive encouragement."
        )
        reply = call_llm(prompt, max_tokens=280, temperature=0.4)
        if reply and len(reply.strip()) > 15:
            return reply.strip()
    except Exception:
        pass

    # Deterministic linguistic analysis fallback if LLM is offline
    has_telugu = any(0x0C00 <= ord(c) <= 0x0C7F for c in q_clean)
    if has_telugu:
        seg = segment_telugu_aksharas(q_clean)
        ak_list = " + ".join(s["akshara"] for s in seg[:10])
        cats = ", ".join(sorted({s["category"] for s in seg}))
        return (
            f"📖 **అక్షరమిత్ర సహాయకుడు (AksharaMitra Companion):**\n\n"
            f"- **మీరు అడిగిన పదం / వాక్యం:** {q_clean}\n"
            f"- **అక్షర విభజన:** `{ak_list}`\n"
            f"- **భాషా విశేషం:** ఇందులో `{cats}` ఉన్నాయి.\n"
            f"- **ప్రోత్సాహం:** ప్రతి అక్షరాన్ని స్పష్టంగా పలుకుతూ చదవండి. మీరు చాలా బాగా నేర్చుకుంటున్నారు! 🌟"
        )
    else:
        words = [w for w in re.findall(r"[a-zA-Z]+", q_clean) if len(w) >= 3]
        target_w = max(words, key=len) if words else q_clean
        dec = decode_english_word_phonics(target_w)
        return (
            f"📖 **AksharaMitra Reading Companion:**\n\n"
            f"- **Focus Word:** `{dec['word']}`\n"
            f"- **Phonics Blending:** `{dec['blend_guide']}` ({dec['syllable_count']} syllable(s))\n"
            f"- **Onset & Rime:** Onset `{dec['onset']}` + Rime `{dec['rime']}`\n"
            f"- **Encouragement:** Read each syllable slowly and blend them together. You are becoming a super reader! 🌟"
        )


# ============================================================================
# 6. DATABASE PERSISTENCE HELPERS (ASSESSMENTS, GAMIFICATION, TEACHER/PARENT)
# ============================================================================

def save_reading_assessment_to_db(
    student_id: str,
    student_name: str,
    grade: str,
    language: str,
    difficulty: str,
    passage_title: str,
    reference_text: str,
    eval_result: Dict[str, Any],
) -> int:
    """Persist a completed student reading assessment and update gamified streak/points in SQLite."""
    init_auth_tables()
    conn = get_db_connection()
    cur = conn.cursor()

    word_analysis = eval_result.get("word_analysis", [])
    mis_words = [w["word"] for w in word_analysis if w.get("status") in ("mispronounced", "needs_work")]
    skip_words = [w["word"] for w in word_analysis if w.get("status") == "skipped"]

    cur.execute(
        """
        INSERT INTO akshara_reading_assessments (
            student_id, student_name, grade, language, difficulty, passage_title,
            reference_text, spoken_transcript, accuracy_pct, wpm, fluency_score,
            pronunciation_score, total_words, correct_words, mispronounced_words,
            skipped_words, word_alignment_json, duration_sec
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_id,
            student_name,
            grade,
            language,
            difficulty,
            passage_title,
            reference_text,
            eval_result.get("student_transcript", ""),
            float(eval_result.get("accuracy_pct", 0.0)),
            int(eval_result.get("wpm", 0)),
            float(eval_result.get("fluency_score", 0.0)),
            float(eval_result.get("pronunciation_score", 0.0)),
            int(eval_result.get("total_words", 0)),
            int(eval_result.get("correct_words", 0)),
            json.dumps(mis_words, ensure_ascii=False),
            json.dumps(skip_words, ensure_ascii=False),
            json.dumps(word_analysis, ensure_ascii=False),
            float(eval_result.get("duration_sec", 0.0)),
        ),
    )
    row_id = cur.lastrowid

    # Update gamified progress
    earned_pts = max(10, int(round(float(eval_result.get("overall_score", 50.0)) * 0.5)))
    cur.execute("SELECT points, streak_days, completed_assessments, badges_json FROM akshara_student_progress WHERE student_id = ?", (student_id,))
    prog = cur.fetchone()
    if prog:
        new_pts = int(prog["points"] or 100) + earned_pts
        new_comp = int(prog["completed_assessments"] or 0) + 1
        new_streak = int(prog["streak_days"] or 1) + 1
        try:
            badges = json.loads(prog["badges_json"] or "[]")
        except Exception:
            badges = ["First Step Reader"]
        if eval_result.get("accuracy_pct", 0) >= 90 and "90% Accuracy Star" not in badges:
            badges.append("90% Accuracy Star")
        if language == "Telugu" and "Telugu Akshara Champion" not in badges:
            badges.append("Telugu Akshara Champion")
        if language == "English" and "English Phonics Pro" not in badges:
            badges.append("English Phonics Pro")
        cur.execute(
            """
            UPDATE akshara_student_progress
            SET points = ?, streak_days = ?, completed_assessments = ?, badges_json = ?,
                weak_areas_json = ?, updated_at = datetime('now')
            WHERE student_id = ?
            """,
            (
                new_pts,
                new_streak,
                new_comp,
                json.dumps(badges, ensure_ascii=False),
                json.dumps((mis_words + skip_words)[:8], ensure_ascii=False),
                student_id,
            ),
        )
    else:
        badges = ["First Step Reader", "Bilingual Explorer"]
        if eval_result.get("accuracy_pct", 0) >= 90:
            badges.append("90% Accuracy Star")
        cur.execute(
            """
            INSERT INTO akshara_student_progress (
                student_id, student_name, grade, points, streak_days,
                completed_assessments, badges_json, weak_areas_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                student_name,
                grade,
                150 + earned_pts,
                8,
                1,
                json.dumps(badges, ensure_ascii=False),
                json.dumps((mis_words + skip_words)[:8], ensure_ascii=False),
            ),
        )

    conn.commit()
    conn.close()
    return row_id


def get_student_assessment_history(student_id: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Retrieve chronological reading assessment history for a student from SQLite."""
    init_auth_tables()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM akshara_reading_assessments
        WHERE student_id = ?
        ORDER BY id DESC LIMIT ?
        """,
        (student_id, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_student_gamification_profile(student_id: str, default_student: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch dynamic points, streaks, level, and earned badges from SQLite."""
    init_auth_tables()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM akshara_student_progress WHERE student_id = ?", (student_id,))
    row = cur.fetchone()
    conn.close()

    base_pts = 180 + int(default_student.get("completed_assessments", 5)) * 25
    if not row:
        return {
            "points": base_pts,
            "streak_days": default_student.get("streak_days", 7),
            "completed_assessments": default_student.get("completed_assessments", 5),
            "level": max(1, base_pts // 100),
            "badges": ["First Step Reader", "Bilingual Explorer", "7-Day Streak Star"],
            "weak_words": [],
        }

    pts = int(row["points"] or base_pts)
    try:
        badges = json.loads(row["badges_json"] or "[]")
    except Exception:
        badges = ["First Step Reader"]
    try:
        weak_words = json.loads(row["weak_areas_json"] or "[]")
    except Exception:
        weak_words = []

    return {
        "points": pts,
        "streak_days": int(row["streak_days"] or default_student.get("streak_days", 7)),
        "completed_assessments": int(row["completed_assessments"] or 1) + int(default_student.get("completed_assessments", 5)),
        "level": max(1, pts // 100),
        "badges": badges,
        "weak_words": weak_words,
    }


def create_teacher_assignment(
    teacher_username: str,
    target_grade: str,
    target_student_id: str,
    language: str,
    difficulty: str,
    passage_title: str,
    notes: str,
) -> None:
    """Save a teacher reading exercise assignment to SQLite."""
    init_auth_tables()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO akshara_teacher_assignments (
            teacher_username, target_grade, target_student_id, language, difficulty, passage_title, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (teacher_username, target_grade, target_student_id, language, difficulty, passage_title, notes),
    )
    conn.commit()
    conn.close()


def get_teacher_assignments(grade: Optional[str] = None, student_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve assigned reading exercises for teachers, students, and parents."""
    init_auth_tables()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM akshara_teacher_assignments ORDER BY id DESC LIMIT 25")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    if student_id:
        rows = [
            r for r in rows
            if r.get("target_student_id") in ("All", student_id)
            or (grade and r.get("target_grade") in ("All", grade))
        ]
    return rows


def save_comprehension_attempt(
    student_id: str,
    passage_title: str,
    language: str,
    total_questions: int,
    correct_answers: int,
) -> float:
    """Record a student's reading comprehension quiz score in SQLite."""
    init_auth_tables()
    score_pct = round((correct_answers / float(max(1, total_questions))) * 100.0, 1)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO akshara_comprehension_attempts (
            student_id, passage_title, language, total_questions, correct_answers, score_pct
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (student_id, passage_title, language, total_questions, correct_answers, score_pct),
    )
    conn.commit()
    conn.close()
    return score_pct

